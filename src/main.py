from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware  # type: ignore[import-untyped]
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.controllers.chat_controller import router as chat_router
from src.controllers.session_controller import router as session_router
from src.controllers.health_controller import router as health_router
from src.repositories import vector_repository, session_repository
from src.services import llm_service
from src.core.middleware import LoggingMiddleware
from src.core.dependencies import verify_api_key
from src.core.rate_limit import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    vector_repository.init()
    llm_service.init()
    session_repository.init()
    yield

app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7860", "http://127.0.0.1:7860"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, dependencies=[Depends(verify_api_key)])
app.include_router(session_router, dependencies=[Depends(verify_api_key)])
app.include_router(health_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
