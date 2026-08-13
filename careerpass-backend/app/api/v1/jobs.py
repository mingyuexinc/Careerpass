"""Authenticated HR-owned Job upload endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_job_upload_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.job_upload import JobUploadResponse
from app.schemas.response import success_response
from app.services.job_upload_service import JobUploadInput, JobUploadService

jobs_router = APIRouter(tags=["jobs"])


@jobs_router.post("/jobs")
async def upload_jobs(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[JobUploadService, Depends(get_job_upload_service)],
    files: Annotated[list[UploadFile], File()],
) -> dict[str, object]:
    if identity.active_role != "hr" or identity.hr_profile_id is None:
        raise AppException(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="HR identity required",
        )
    if not files:
        raise AppException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="at least one file is required",
        )

    value = await service.upload_many(
        hr_profile_id=identity.hr_profile_id,
        uploads=[
            JobUploadInput(
                content=await file.read(),
                filename=file.filename,
                declared_mime=file.content_type,
            )
            for file in files
        ],
    )
    response = JobUploadResponse.model_validate(value)
    return success_response(
        response.model_dump(mode="json"),
        msg="job upload processed",
        code=ErrorCode.SUCCESS,
    )
