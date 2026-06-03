from contextvars import ContextVar
import uuid
from fastapi import Request

request_id_ctx_var: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_id_ctx_var.set(request_id)
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
