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
                stages = json.loads(row.get("stages") or "[]")
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


def list_recent_traces(limit: int = 20) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT trace_id, user_id, session_id, status, route_agent, duration_ms, error_message, created_at, updated_at
                FROM agent_call_traces
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return list(cursor.fetchall())