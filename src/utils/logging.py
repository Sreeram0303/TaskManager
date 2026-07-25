import logging
import time
import uuid
from contextvars import ContextVar
from fastapi import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger("taskmanager")
logging.basicConfig(level=logging.INFO)

async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)          # ← fresh value, set HERE, once per request

    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    logger.info(f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")
    return response
