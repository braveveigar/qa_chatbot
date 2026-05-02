import time
import uuid
import logging
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("qa_chatbot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        request_id_var.set(request_id)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000

        logger.info(
            "[%s] %s %s → %s (%.0fms)",
            request_id, request.method, request.url.path, response.status_code, elapsed,
        )
        response.headers["X-Request-ID"] = request_id
        return response
