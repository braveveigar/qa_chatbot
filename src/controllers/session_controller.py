from fastapi import APIRouter
from src.models.chat import SessionResetRequest
from src.repositories import session_repository

router = APIRouter()

@router.post("/session/reset")
async def reset_session(data: SessionResetRequest):
    session_repository.clear(data.session_id)
    return {"status": "ok"}
