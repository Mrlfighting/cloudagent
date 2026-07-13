from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from infra.db import get_db_connection


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_execute(operation):
    try:
        return operation()
    except Exception as exc:
        print(f"[Trace] write skipped: {exc}")
        return None


def _decode_stages(stages: Any) -> list[dict[str, Any]]:
    if not stages:
        return []
    if isinstance(stages, list):
        return stages
    try:
        decoded = json.loads(stages)
    except (TypeError, json.JSONDecodeError):
        return []
    return decoded if isinstance(decoded, list) else []


def _format_trace(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    row["stages"] = _decode_stages(row.get("stages"))
    return row


def start_trace(user_id: str, session_id: str, query: str) -> str | None:
    trace_id = f"trace_{uuid.uuid4().hex}"

    def operation():
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_call_traces (trace_id, user_id, session_id, query, status, stages)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (trace_id, user_id, session_id, query, "started", json.dumps([], ensure_ascii=False)),
                )
        return trace_id

    return _safe_execute(operation)


def append_trace_stage(trace_id: str | None, status: str, message: str) -> None:
    if not trace_id:
        return

    def operation():
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT stages FROM agent_call_traces WHERE trace_id = %s LIMIT 1",
                    (trace_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return
                stages = _decode_stages(row.get("stages"))
                stages.append({"status": status, "message": message, "at": _utc_iso()})
                cursor.execute(
                    """
                    UPDATE agent_call_traces
                    SET status = %s, stages = %s, updated_at = NOW()
                    WHERE trace_id = %s
                    """,
                    (status, json.dumps(stages, ensure_ascii=False), trace_id),
                )

    _safe_execute(operation)


def finish_trace(
    trace_id: str | None,
    *,
    status: str,
    route_agent: str | None,
    duration_ms: int,
    error_message: str | None = None,
) -> None:
    if not trace_id:
        return

    def operation():
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE agent_call_traces
                    SET status = %s,
                        route_agent = %s,
                        duration_ms = %s,
                        error_message = %s,
                        updated_at = NOW()
                    WHERE trace_id = %s
                    """,
                    (status, route_agent, duration_ms, error_message, trace_id),
                )

    _safe_execute(operation)


def list_recent_traces(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 100))
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT trace_id, user_id, session_id, query, status, route_agent, stages,
                       duration_ms, error_message, created_at, updated_at
                FROM agent_call_traces
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (user_id, safe_limit),
            )
            return [_format_trace(row) for row in cursor.fetchall()]


def list_session_traces(user_id: str, session_id: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT trace_id, user_id, session_id, query, status, route_agent, stages,
                       duration_ms, error_message, created_at, updated_at
                FROM agent_call_traces
                WHERE user_id = %s AND session_id = %s
                ORDER BY id DESC
                """,
                (user_id, session_id),
            )
            return [_format_trace(row) for row in cursor.fetchall()]
