"""Authenticated read API for document-parsing results."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_document_parsing_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.response import success_response
from app.services.document_parsing_service import DocumentParsingService

document_parsing_router = APIRouter(tags=["document-parsing"])


@document_parsing_router.get("/resumes/{resume_id}/profile")
async def get_resume_profile(
    resume_id: UUID,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[DocumentParsingService, Depends(get_document_parsing_service)],
) -> dict[str, object]:
    """Return only a profile that belongs to the current candidate and is fully validated."""
    value = await service.get_profile(identity.candidate_id, resume_id)
    if value is None:
        raise AppException(status_code=404, code=ErrorCode.NOT_FOUND, message="profile not found")
    return success_response(value.model_dump(mode="json"))
