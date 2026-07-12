from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    query: str
    session_id: str

class ChatResponse(BaseModel):
    status: str
    reply: str
    user_id: str
    session_id: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_at: str
    user: UserResponse


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    last_message: Optional[str] = None
    message_count: int = 0


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str
