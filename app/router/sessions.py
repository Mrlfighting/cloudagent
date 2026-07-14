from fastapi import APIRouter, Response, status

from schemas.chat import CreateSessionRequest
from service.auth_service import CurrentUser
from service.session_service import (
    create_session,
    list_messages,
    list_sessions,
    soft_delete_session,
)

router = APIRouter()


@router.get("/sessions")
async def get_sessions(current_user: dict = CurrentUser):
    return list_sessions(current_user["user_id"])


@router.post("/sessions")
async def post_session(request: CreateSessionRequest, current_user: dict = CurrentUser):
    return create_session(current_user["user_id"], request.title)


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, current_user: dict = CurrentUser):
    return list_messages(current_user["user_id"], session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, current_user: dict = CurrentUser):
    soft_delete_session(current_user["user_id"], session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
