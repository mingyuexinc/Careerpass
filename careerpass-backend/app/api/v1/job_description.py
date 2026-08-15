"""Internal S-03 verification endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_job_description_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.job_description import JobDescriptionParseSubmitRequest
from app.schemas.response import success_response
from app.services.job_description_service import (
    JobDescriptionInputUnavailableError,
    JobDescriptionService,
)

job_description_router = APIRouter(
    prefix="/internal/v1/s03/job-description/parses",
    tags=["internal-s03"],
)


def _require_hr(identity: CurrentIdentity) -> UUID:
    if identity.active_role != "hr" or identity.hr_profile_id is None:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="HR identity required",
        )
    return identity.hr_profile_id


@job_description_router.post("")
async def submit_job_description_parse(
    payload: JobDescriptionParseSubmitRequest,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[JobDescriptionService, Depends(get_job_description_service)],
) -> dict[str, object]:
    try:
        data = await service.submit(
            hr_profile_id=_require_hr(identity),
            local_path=payload.local_path,
        )
    except JobDescriptionInputUnavailableError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.VALIDATION_ERROR,
            message="controlled JD input unavailable",
        ) from None
    return success_response(data.model_dump(mode="json"), msg="job description parse queued")


@job_description_router.get("/{task_id}")
async def get_job_description_parse(
    task_id: UUID,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[JobDescriptionService, Depends(get_job_description_service)],
) -> dict[str, object]:
    result = await service.get_result(
        hr_profile_id=_require_hr(identity),
        task_id=task_id,
    )
    if result is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.NOT_FOUND,
            message="parse task not found",
        )
    return success_response(result.model_dump(mode="json"), msg="job description parse status")
