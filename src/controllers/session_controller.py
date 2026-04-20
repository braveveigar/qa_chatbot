from fastapi import APIRouter
from src.repositories import session_repository

router = APIRouter()

@router.post("/session/reset")
async def reset_session():
    session_repository.clear()
    return {"status": "ok"}
