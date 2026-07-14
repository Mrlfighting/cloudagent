from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from schemas.chat import ChatRequest
from service.auth_service import CurrentUser
from service.chat_service import stream_chat
from service.session_service import get_session_or_404

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, current_user: dict = CurrentUser):
    """
    处理多智能体聊天请求，并使用 SSE (Server-Sent Events) 返回流式响应。
    如果命中 L1 语义缓存，将直接返回缓存结果。
    否则进入 Agent 图编排流程。
    """
    get_session_or_404(current_user["user_id"], request.session_id)
    return StreamingResponse(
        stream_chat(request.query, current_user["user_id"], request.session_id),
        media_type="text/event-stream"
    )
