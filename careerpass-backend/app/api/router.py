"""Non-business routes owned by the API layer."""

from fastapi import APIRouter

from app.api.v1.auth import auth_router
from app.api.v1.candidate_preparation import candidate_preparation_router
from app.api.v1.document_parsing import document_parsing_router
from app.api.v1.health import health_router
from app.api.v1.jobs import jobs_router
from app.core.config import get_settings
from app.schemas.response import success_response

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(candidate_preparation_router, prefix="/api/v1")
api_router.include_router(document_parsing_router, prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(jobs_router, prefix="/api/v1")


@api_router.get("/", tags=["system"])
async def application_metadata() -> dict[str, object]:
    """Return the stable response envelope without probing dependencies."""
    settings = get_settings()
    return success_response({"service": settings.app_name})
