"""HTTP middleware that establishes safe request observability."""

import logging
from time import perf_counter

from fastapi import Request
from starlette.responses import Response

from app.core.request_context import (
    REQUEST_ID_HEADER,
    reset_request_id,
    resolve_request_id,
    set_request_id,
)

logger = logging.getLogger("careerpass.request")


async def request_context_middleware(request: Request, call_next) -> Response:
    """Attach correlation data and log only method, path, status and latency."""
    request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    context_token = set_request_id(request_id)
    started_at = perf_counter()
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        return response
    finally:
        reset_request_id(context_token)
