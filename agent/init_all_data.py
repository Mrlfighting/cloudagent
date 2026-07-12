import os
import sys
import json
import pymysql
from passlib.context import CryptContext

agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(agent_dir)

from test.build_kg import import_to_neo4j
from test.milvus_rag import MilvusRAGManager
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(agent_dir)
MOCK_DATA_DIR = os.path.join(BASE_DIR, "mock_data")
load_dotenv(os.path.join(agent_dir, ".env"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_PASSWORD = "Cloud@123456"


def seed_users(cursor):
    users = [
        ("user_1001", "user_1001", "用户 1001"),
        ("user_1002", "user_1002", "用户 1002"),
    ]
    for user_id, username, display_name in users:
        cursor.execute(
            """
            INSERT INTO users (user_id, username, display_name, password_hash, disabled)
            VALUES (%s, %s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                display_name = VALUES(display_name),
                disabled = 0
            """,
            (user_id, username, display_name, pwd_context.hash(DEFAULT_PASSWORD)),
        )

def init_mysql():
    print("\n=== 1. 初始化 MySQL 业务数据 ===")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", 3306))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "root123")
    
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS cloud_platform DEFAULT CHARACTER SET utf8mb4;")
        cursor.execute("USE cloud_platform;")
        
        sql_path = os.path.join(agent_dir, "database", "init_mock_data.sql")
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
            
        # 简单按分号分割执行
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        seed_users(cursor)
        conn.commit()
        print(f"默认登录账号: user_1001 / user_1002，默认密码: {DEFAULT_PASSWORD}")
        print("MySQL 数据导入成功！")
    except Exception as e:
        print(f"MySQL 导入失败: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

def init_neo4j():
    print("\n=== 2. 初始化 Neo4j 知识图谱 ===")
    try:
        for file in os.listdir(MOCK_DATA_DIR):
            if file.endswith('.json'):
                path = os.path.join(MOCK_DATA_DIR, file)
                print(f"正在读取并导入图谱: {file}")
                with open(path, 'r', encoding='utf-8') as f:
                    kg_data = json.load(f)
                    import_to_neo4j(kg_data)
    except Exception as e:
        print(f"Neo4j 导入失败: {e}")

def init_milvus():
    print("\n=== 3. 初始化 Milvus 向量库 ===")
    try:
        manager = MilvusRAGManager()
        manager.ingest_documents(MOCK_DATA_DIR)
    except Exception as e:
        print(f"Milvus 导入失败: {e}")

if __name__ == "__main__":
    init_mysql()
    init_neo4j()
    init_milvus()
    print("\n🎉 所有数据库初始化完成！")
