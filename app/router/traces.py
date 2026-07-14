from fastapi import APIRouter, Query

from service.agent_trace_service import list_recent_traces, list_session_traces
from service.auth_service import CurrentUser
from service.session_service import get_session_or_404

router = APIRouter()


@router.get("/traces/recent")
def recent_traces(limit: int = Query(default=20, ge=1, le=100), current_user: dict = CurrentUser):
    return list_recent_traces(current_user["user_id"], limit)


@router.get("/sessions/{session_id}/traces")
def session_traces(session_id: str, current_user: dict = CurrentUser):
    get_session_or_404(current_user["user_id"], session_id)
    return list_session_traces(current_user["user_id"], session_id)
