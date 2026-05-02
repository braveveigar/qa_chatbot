from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.repositories import session_repository, vector_repository
from src.services import llm_service

router = APIRouter()

@router.get("/health")
async def health():
    redis_ok = False
    try:
        if session_repository.redis_client is not None:
            session_repository.redis_client.ping()
            redis_ok = True
    except Exception:
        redis_ok = False

    milvus_ok = vector_repository.is_connected()
    openai_ok = llm_service.is_ready()

    all_ok = redis_ok and milvus_ok and openai_ok
    body = {
        "status": "ok" if all_ok else "degraded",
        "redis": "ok" if redis_ok else "error",
        "milvus": "ok" if milvus_ok else "error",
        "openai": "ok" if openai_ok else "error",
    }
    return JSONResponse(content=body, status_code=200 if all_ok else 503)
