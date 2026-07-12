from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status

from infra.db import get_db_connection


def create_session(user_id: str, title: str | None = None) -> dict[str, Any]:
    session_id = f"session_{uuid.uuid4().hex}"
    session_title = (title or "新对话").strip()[:100] or "新对话"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_sessions (session_id, user_id, title)
                VALUES (%s, %s, %s)
                """,
                (session_id, user_id, session_title),
            )
    return get_session_or_404(user_id, session_id)


def list_sessions(user_id: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.session_id,
                    s.title,
                    s.created_at,
                    s.updated_at,
                    (
                        SELECT m.content
                        FROM chat_messages m
                        WHERE m.session_id = s.session_id
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) AS last_message,
                    (
                        SELECT COUNT(*)
                        FROM chat_messages m
                        WHERE m.session_id = s.session_id
                    ) AS message_count
                FROM chat_sessions s
                WHERE s.user_id = %s AND s.deleted_at IS NULL
                ORDER BY s.updated_at DESC
                """,
                (user_id,),
            )
            return list(cursor.fetchall())


def get_session_or_404(user_id: str, session_id: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, user_id, title, created_at, updated_at
                FROM chat_sessions
                WHERE session_id = %s AND user_id = %s AND deleted_at IS NULL
                LIMIT 1
                """,
                (session_id, user_id),
            )
            session = cursor.fetchone()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def list_messages(user_id: str, session_id: str) -> list[dict[str, Any]]:
    get_session_or_404(user_id, session_id)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, role, content, created_at
                FROM chat_messages
                WHERE session_id = %s AND user_id = %s
                ORDER BY id ASC
                """,
                (session_id, user_id),
            )
            return list(cursor.fetchall())


def soft_delete_session(user_id: str, session_id: str) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE chat_sessions
                SET deleted_at = NOW(), updated_at = NOW()
                WHERE session_id = %s AND user_id = %s AND deleted_at IS NULL
                """,
                (session_id, user_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


def append_message(user_id: str, session_id: str, role: str, content: str) -> None:
    get_session_or_404(user_id, session_id)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages (session_id, user_id, role, content)
                VALUES (%s, %s, %s, %s)
                """,
                (session_id, user_id, role, content),
            )
            if role == "user":
                title = content.strip().replace("\n", " ")[:40] or "新对话"
                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET title = IF(title = '新对话', %s, title), updated_at = NOW()
                    WHERE session_id = %s AND user_id = %s
                    """,
                    (title, session_id, user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET updated_at = NOW()
                    WHERE session_id = %s AND user_id = %s
                    """,
                    (session_id, user_id),
                )
