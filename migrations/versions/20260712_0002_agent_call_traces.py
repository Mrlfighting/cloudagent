"""add agent call traces

Revision ID: 20260712_0002
Revises: 20260712_0001
Create Date: 2026-07-12 00:00:01
"""
from alembic import op

revision = "20260712_0002"
down_revision = "20260712_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_call_traces (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            trace_id VARCHAR(80) NOT NULL UNIQUE COMMENT '调用轨迹ID',
            user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
            session_id VARCHAR(80) NOT NULL COMMENT '会话ID',
            query MEDIUMTEXT NOT NULL COMMENT '用户问题',
            status VARCHAR(40) NOT NULL COMMENT '当前状态',
            route_agent VARCHAR(80) NULL COMMENT '命中的Agent或缓存',
            stages JSON NULL COMMENT '阶段状态列表',
            duration_ms INT NULL COMMENT '总耗时毫秒',
            error_message TEXT NULL COMMENT '失败原因',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_agent_traces_user_created (user_id, created_at),
            INDEX idx_agent_traces_session_created (session_id, created_at),
            INDEX idx_agent_traces_status_created (status, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent调用轨迹表'
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_call_traces")