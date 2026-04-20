from fastapi import APIRouter
from src.repositories import session_repository, vector_repository

router = APIRouter()

@router.get("/health")
async def health():
    redis_ok = True
    try:
        r = session_repository._get_client()
        r.ping()
    except Exception:
        redis_ok = False

    milvus_ok = vector_repository.is_connected()

    status = "ok" if (redis_ok and milvus_ok) else "degraded"
    return {
        "status": status,
        "redis": "ok" if redis_ok else "error",
        "milvus": "ok" if milvus_ok else "error",
    }
