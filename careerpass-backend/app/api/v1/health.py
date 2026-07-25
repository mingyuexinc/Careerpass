"""Safe liveness and readiness endpoints."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.core.errors import ErrorCode
from app.schemas.response import error_response, success_response
from app.services.runtime_health_service import RuntimeHealthService

health_router = APIRouter(prefix="/health", tags=["health"])


@health_router.get("/live")
async def liveness() -> dict[str, object]:
    """Confirm that the HTTP process can receive requests without probing dependencies."""
    return success_response({"status": "alive"})


@health_router.get("/ready", response_model=None)
async def readiness(request: Request) -> dict[str, object] | JSONResponse:
    """Confirm required dependencies within their configured timeout boundaries."""
    health_service: RuntimeHealthService = request.app.state.runtime_health_service
    if await health_service.is_ready():
        return success_response({"status": "ready"})
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response(
            code=ErrorCode.INTERNAL_ERROR,
            msg="service not ready",
        ),
    )
