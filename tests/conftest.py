import os
import sys
from pathlib import Path

import pytest
import pymysql
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from passlib.context import CryptContext

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DASHSCOPE_API_KEY", "test_dashscope_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_USER", "root")
os.environ.setdefault("MYSQL_PASSWORD", "root123")
os.environ.setdefault("MYSQL_DATABASE", "cloud_platform_test")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_cloud_agent_pytest_only_32_chars")

sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "agent"))

from router import auth, chat, sessions  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _connect(database: str | None = None):
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


@pytest.fixture(scope="session")
def test_database():
    db_name = os.environ["MYSQL_DATABASE"]
    try:
        conn = _connect()
    except Exception as exc:
        pytest.skip(f"MySQL is not available for integration tests: {exc}")

    with conn.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    conn.close()

    conn = _connect(db_name)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(50) PRIMARY KEY,
                username VARCHAR(80) NOT NULL UNIQUE,
                display_name VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                disabled TINYINT NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id VARCHAR(80) PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL,
                title VARCHAR(100) NOT NULL DEFAULT '新对话',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at DATETIME NULL,
                INDEX idx_chat_sessions_user_updated (user_id, deleted_at, updated_at),
                CONSTRAINT fk_test_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                session_id VARCHAR(80) NOT NULL,
                user_id VARCHAR(50) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content MEDIUMTEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_chat_messages_session_id (session_id, id),
                INDEX idx_chat_messages_user_id (user_id, created_at),
                CONSTRAINT fk_test_chat_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id),
                CONSTRAINT fk_test_chat_messages_user FOREIGN KEY (user_id) REFERENCES users(user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                token_hash CHAR(64) NOT NULL UNIQUE,
                user_id VARCHAR(50) NOT NULL,
                expires_at DATETIME NOT NULL,
                revoked_at DATETIME NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_refresh_tokens_user_id (user_id),
                INDEX idx_refresh_tokens_expires_at (expires_at),
                CONSTRAINT fk_test_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
    conn.close()
    return db_name


@pytest.fixture(autouse=True)
def reset_database(test_database):
    conn = _connect(test_database)
    with conn.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        for table in ("refresh_tokens", "chat_messages", "chat_sessions", "users"):
            cursor.execute(f"TRUNCATE TABLE {table}")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        password_hash = pwd_context.hash("Cloud@123456")
        cursor.executemany(
            """
            INSERT INTO users (user_id, username, display_name, password_hash, disabled)
            VALUES (%s, %s, %s, %s, 0)
            """,
            [
                ("user_1001", "user_1001", "用户 1001", password_hash),
                ("user_1002", "user_1002", "用户 1002", password_hash),
            ],
        )
    conn.close()


@pytest.fixture
def client(test_database):
    app = FastAPI(title="Cloud Agent Test API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    return TestClient(app)
