from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.controllers.chat_controller import router as chat_router
from src.controllers.session_controller import router as session_router
from src.controllers.health_controller import router as health_router
from src.repositories import vector_repository
from src.services import llm_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    vector_repository.init()
    llm_service.init()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(chat_router)
app.include_router(session_router)
app.include_router(health_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
