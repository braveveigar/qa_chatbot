from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from src.models.chat import ChatRequest
from src.services import chat_service

router = APIRouter()

@router.post("/chat")
async def chat(data: ChatRequest):
    return StreamingResponse(chat_service.process_chat(data.question), media_type="text/plain")
