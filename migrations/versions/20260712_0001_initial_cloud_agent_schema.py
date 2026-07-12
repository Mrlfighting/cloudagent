"""initial cloud agent schema

Revision ID: 20260712_0001
Revises:
Create Date: 2026-07-12 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext

revision = "20260712_0001"
down_revision = None
branch_labels = None
depends_on = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_PASSWORD = "Cloud@123456"

DDL = [
    """
    CREATE TABLE IF NOT EXISTS cloud_orders (
        order_id VARCHAR(50) PRIMARY KEY COMMENT '订单唯一ID',
        user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
        product_name VARCHAR(100) NOT NULL COMMENT '产品名称',
        billing_mode VARCHAR(20) NOT NULL COMMENT '计费模式',
        amount DECIMAL(10, 2) NOT NULL COMMENT '订单金额',
        status VARCHAR(20) NOT NULL COMMENT '订单状态',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        INDEX idx_cloud_orders_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='云产品订单表'
    """,
    """
    CREATE TABLE IF NOT EXISTS cloud_instances (
        instance_id VARCHAR(50) PRIMARY KEY COMMENT '实例唯一ID',
        user_id VARCHAR(50) NOT NULL COMMENT '所属用户',
        order_id VARCHAR(50) NOT NULL COMMENT '关联订单',
        instance_type VARCHAR(100) NOT NULL COMMENT '实例规格',
        region_id VARCHAR(50) NOT NULL COMMENT '地域',
        zone_id VARCHAR(50) NOT NULL COMMENT '可用区',
        status VARCHAR(20) NOT NULL COMMENT '运行状态',
        public_ip VARCHAR(20) COMMENT '公网IP',
        INDEX idx_cloud_instances_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='云资源实例表'
    """,
    """
    CREATE TABLE IF NOT EXISTS instance_metrics_daily (
        id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
        instance_id VARCHAR(50) NOT NULL COMMENT '实例ID',
        user_id VARCHAR(50) NOT NULL COMMENT '所属用户ID',
        metric_date DATE NOT NULL COMMENT '统计日期',
        avg_cpu_usage_percent DECIMAL(5,2) NOT NULL COMMENT '平均CPU利用率',
        avg_memory_usage_percent DECIMAL(5,2) NOT NULL COMMENT '平均内存利用率',
        max_network_out_mbps DECIMAL(8,2) NOT NULL COMMENT '出口带宽峰值',
        INDEX idx_instance_date (instance_id, metric_date),
        INDEX idx_user_instance (user_id, instance_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='实例日级监控指标表'
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR(50) PRIMARY KEY COMMENT '用户ID',
        username VARCHAR(80) NOT NULL UNIQUE COMMENT '登录用户名',
        display_name VARCHAR(100) NOT NULL COMMENT '显示名称',
        password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
        disabled TINYINT NOT NULL DEFAULT 0 COMMENT '是否禁用',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表'
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        session_id VARCHAR(80) PRIMARY KEY COMMENT '会话ID',
        user_id VARCHAR(50) NOT NULL COMMENT '所属用户',
        title VARCHAR(100) NOT NULL DEFAULT '新对话' COMMENT '会话标题',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        deleted_at DATETIME NULL COMMENT '软删除时间',
        INDEX idx_chat_sessions_user_updated (user_id, deleted_at, updated_at),
        CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天会话表'
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        session_id VARCHAR(80) NOT NULL COMMENT '会话ID',
        user_id VARCHAR(50) NOT NULL COMMENT '所属用户',
        role VARCHAR(20) NOT NULL COMMENT 'user/assistant',
        content MEDIUMTEXT NOT NULL COMMENT '消息内容',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_chat_messages_session_id (session_id, id),
        INDEX idx_chat_messages_user_id (user_id, created_at),
        CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id),
        CONSTRAINT fk_chat_messages_user FOREIGN KEY (user_id) REFERENCES users(user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        token_hash CHAR(64) NOT NULL UNIQUE COMMENT '刷新令牌SHA256',
        user_id VARCHAR(50) NOT NULL COMMENT '所属用户',
        expires_at DATETIME NOT NULL COMMENT '过期时间',
        revoked_at DATETIME NULL COMMENT '撤销时间',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_refresh_tokens_user_id (user_id),
        INDEX idx_refresh_tokens_expires_at (expires_at),
        CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='刷新令牌表'
    """,
]


def upgrade() -> None:
    connection = op.get_bind()
    for statement in DDL:
        op.execute(statement)

    password_hash = pwd_context.hash(DEFAULT_PASSWORD)
    connection.execute(
        sa.text(
            """
            INSERT INTO users (user_id, username, display_name, password_hash, disabled)
            VALUES (:user_id, :username, :display_name, :password_hash, 0)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                display_name = VALUES(display_name),
                password_hash = VALUES(password_hash),
                disabled = 0
            """
        ),
        [
            {"user_id": "user_1001", "username": "user_1001", "display_name": "用户 1001", "password_hash": password_hash},
            {"user_id": "user_1002", "username": "user_1002", "display_name": "用户 1002", "password_hash": password_hash},
        ],
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO cloud_orders (order_id, user_id, product_name, billing_mode, amount, status, created_at)
            VALUES (:order_id, :user_id, :product_name, :billing_mode, :amount, :status, :created_at)
            ON DUPLICATE KEY UPDATE product_name = VALUES(product_name), billing_mode = VALUES(billing_mode), amount = VALUES(amount), status = VALUES(status)
            """
        ),
        [
            {"order_id": "ORD-1001-001", "user_id": "user_1001", "product_name": "ecs.g8a.4xlarge", "billing_mode": "包年包月", "amount": 12500.00, "status": "Paid", "created_at": "2023-10-01 10:00:00"},
            {"order_id": "ORD-1001-002", "user_id": "user_1001", "product_name": "rds.mysql.c1.large", "billing_mode": "包年包月", "amount": 3600.00, "status": "Paid", "created_at": "2023-10-05 14:30:00"},
            {"order_id": "ORD-1001-003", "user_id": "user_1001", "product_name": "共享带宽 100Mbps", "billing_mode": "按量付费", "amount": 150.50, "status": "Paid", "created_at": "2023-11-01 08:15:00"},
            {"order_id": "ORD-1002-001", "user_id": "user_1002", "product_name": "ecs.c7.large", "billing_mode": "按量付费", "amount": 45.20, "status": "Paid", "created_at": "2023-11-15 09:00:00"},
            {"order_id": "ORD-1002-002", "user_id": "user_1002", "product_name": "云盘 ESSD PL0 40G", "billing_mode": "包年包月", "amount": 120.00, "status": "Paid", "created_at": "2023-11-15 09:05:00"},
            {"order_id": "ORD-1002-003", "user_id": "user_1002", "product_name": "ecs.c7.large", "billing_mode": "按量付费", "amount": 12.80, "status": "Unpaid", "created_at": "2023-11-16 10:00:00"},
        ],
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO cloud_instances (instance_id, user_id, order_id, instance_type, region_id, zone_id, status, public_ip)
            VALUES (:instance_id, :user_id, :order_id, :instance_type, :region_id, :zone_id, :status, :public_ip)
            ON DUPLICATE KEY UPDATE instance_type = VALUES(instance_type), region_id = VALUES(region_id), zone_id = VALUES(zone_id), status = VALUES(status), public_ip = VALUES(public_ip)
            """
        ),
        [
            {"instance_id": "i-bp1_user1001_ecs", "user_id": "user_1001", "order_id": "ORD-1001-001", "instance_type": "ecs.g8a.4xlarge", "region_id": "cn-beijing", "zone_id": "cn-beijing-k", "status": "Running", "public_ip": "47.100.1.1"},
            {"instance_id": "rm-bp1_user1001_rds", "user_id": "user_1001", "order_id": "ORD-1001-002", "instance_type": "rds.mysql.c1.large", "region_id": "cn-beijing", "zone_id": "cn-beijing-l", "status": "Running", "public_ip": None},
            {"instance_id": "i-bp1_user1002_ecs", "user_id": "user_1002", "order_id": "ORD-1002-001", "instance_type": "ecs.c7.large", "region_id": "cn-hangzhou", "zone_id": "cn-hangzhou-h", "status": "Stopped", "public_ip": "114.55.2.2"},
        ],
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO instance_metrics_daily (instance_id, user_id, metric_date, avg_cpu_usage_percent, avg_memory_usage_percent, max_network_out_mbps)
            VALUES (:instance_id, :user_id, DATE_SUB(CURDATE(), INTERVAL :days_ago DAY), :cpu, :memory, :bandwidth)
            """
        ),
        [
            {"instance_id": "i-bp1_user1001_ecs", "user_id": "user_1001", "days_ago": 6, "cpu": 2.10, "memory": 18.50, "bandwidth": 1.20},
            {"instance_id": "i-bp1_user1001_ecs", "user_id": "user_1001", "days_ago": 5, "cpu": 2.50, "memory": 19.10, "bandwidth": 1.60},
            {"instance_id": "i-bp1_user1001_ecs", "user_id": "user_1001", "days_ago": 4, "cpu": 3.20, "memory": 20.40, "bandwidth": 2.00},
            {"instance_id": "i-bp1_user1001_ecs", "user_id": "user_1001", "days_ago": 3, "cpu": 1.90, "memory": 17.90, "bandwidth": 1.00},
            {"instance_id": "i-bp1_user1001_ecs", "user_id": "user_1001", "days_ago": 2, "cpu": 2.80, "memory": 18.20, "bandwidth": 1.40},
            {"instance_id": "i-bp1_user1001_ecs", "user_id": "user_1001", "days_ago": 1, "cpu": 2.40, "memory": 19.00, "bandwidth": 1.30},
            {"instance_id": "i-bp1_user1001_ecs", "user_id": "user_1001", "days_ago": 0, "cpu": 2.00, "memory": 18.70, "bandwidth": 1.10},
            {"instance_id": "i-bp1_user1002_ecs", "user_id": "user_1002", "days_ago": 6, "cpu": 36.50, "memory": 62.10, "bandwidth": 42.00},
            {"instance_id": "i-bp1_user1002_ecs", "user_id": "user_1002", "days_ago": 5, "cpu": 41.20, "memory": 65.00, "bandwidth": 51.00},
            {"instance_id": "i-bp1_user1002_ecs", "user_id": "user_1002", "days_ago": 4, "cpu": 38.40, "memory": 63.50, "bandwidth": 48.00},
            {"instance_id": "i-bp1_user1002_ecs", "user_id": "user_1002", "days_ago": 3, "cpu": 44.00, "memory": 67.30, "bandwidth": 55.00},
            {"instance_id": "i-bp1_user1002_ecs", "user_id": "user_1002", "days_ago": 2, "cpu": 39.10, "memory": 60.80, "bandwidth": 47.00},
            {"instance_id": "i-bp1_user1002_ecs", "user_id": "user_1002", "days_ago": 1, "cpu": 42.80, "memory": 64.20, "bandwidth": 53.00},
            {"instance_id": "i-bp1_user1002_ecs", "user_id": "user_1002", "days_ago": 0, "cpu": 40.30, "memory": 61.90, "bandwidth": 49.00},
        ],
    )


def downgrade() -> None:
    for table in [
        "refresh_tokens",
        "chat_messages",
        "chat_sessions",
        "instance_metrics_daily",
        "cloud_instances",
        "cloud_orders",
        "users",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table}")