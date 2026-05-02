from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from src.models.chat import ChatRequest
from src.services import chat_service
from src.core.rate_limit import limiter

router = APIRouter()

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, data: ChatRequest):
    return StreamingResponse(
        chat_service.process_chat(data.session_id, data.question),
        media_type="text/plain",
    )
