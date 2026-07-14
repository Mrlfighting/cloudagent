from fastapi import APIRouter, HTTPException, status

from schemas.chat import LoginRequest, LogoutRequest, RefreshRequest
from service.auth_service import (
    CurrentUser,
    authenticate_user,
    issue_token_pair,
    public_user,
    refresh_token_pair,
    revoke_refresh_token,
)

router = APIRouter()


@router.post("/auth/login")
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    try:
        return issue_token_pair(user)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/auth/refresh")
async def refresh(request: RefreshRequest):
    try:
        return refresh_token_pair(request.refresh_token)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/auth/logout")
async def logout(request: LogoutRequest, current_user: dict = CurrentUser):
    revoke_refresh_token(request.refresh_token)
    return {"status": "ok", "user_id": current_user["user_id"]}


@router.get("/auth/me")
async def me(current_user: dict = CurrentUser):
    return public_user(current_user)
