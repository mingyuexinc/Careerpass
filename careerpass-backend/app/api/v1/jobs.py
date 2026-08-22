"""Authenticated HR-owned Job upload endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import (
    get_business_resource_deletion_service,
    get_job_description_service,
    get_job_service,
    get_job_upload_service,
)
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.repositories.business_resource_deletion_repository import (
    DeletionNotAllowedError,
    DeletionOwnershipError,
    DeletionResourceNotFoundError,
)
from app.repositories.job_description_repository import (
    JobDescriptionRetryNotAllowedError,
    JobDescriptionTaskPreconditionError,
)
from app.schemas.business_resource_deletion import ResourceDeletionResponse
from app.schemas.job import HrJobListResponse
from app.schemas.job_upload import JobUploadResponse
from app.schemas.response import success_response
from app.services.business_resource_deletion_service import BusinessResourceDeletionService
from app.services.job_description_service import JobDescriptionService
from app.services.job_service import JobService
from app.services.job_upload_service import JobUploadInput, JobUploadService

jobs_router = APIRouter(tags=["jobs"])


@jobs_router.get("/jobs/hr/current")
async def get_current_hr_jobs(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> dict[str, object]:
    if identity.active_role != "hr" or identity.hr_profile_id is None:
        raise AppException(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="HR identity required",
        )
    jobs = await service.list_current_for_hr(hr_profile_id=identity.hr_profile_id)
    response = HrJobListResponse(jobs=jobs, total=len(jobs))
    return success_response(
        response.model_dump(mode="json"),
        msg="current HR jobs",
        code=ErrorCode.SUCCESS,
    )


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


@jobs_router.post("/jobs/{job_id}/parse/retry")
async def retry_job_parse(
    job_id: UUID,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[JobDescriptionService, Depends(get_job_description_service)],
) -> dict[str, object]:
    if identity.active_role != "hr" or identity.hr_profile_id is None:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="HR identity required")
    try:
        result = await service.retry_failed_job(
            hr_profile_id=identity.hr_profile_id,
            job_id=job_id,
        )
    except JobDescriptionTaskPreconditionError:
        raise AppException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="岗位不存在或不可用",
        ) from None
    except JobDescriptionRetryNotAllowedError:
        raise AppException(
            status_code=409,
            code=ErrorCode.PRECONDITION_NOT_MET,
            message="该岗位当前不可重新解析",
        ) from None
    return success_response(result.model_dump(mode="json"), msg="job JD parse retry queued")


@jobs_router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: UUID,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[BusinessResourceDeletionService, Depends(get_business_resource_deletion_service)],
) -> dict[str, object]:
    if identity.active_role != "hr" or identity.hr_profile_id is None:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="HR identity required")
    try:
        result = await service.delete_job(
            hr_profile_id=identity.hr_profile_id,
            job_id=job_id,
            actor_user_id=identity.user_id,
            actor_role=identity.active_role,
        )
    except DeletionResourceNotFoundError:
        raise AppException(status_code=404, code=ErrorCode.NOT_FOUND, message="resource not found") from None
    except DeletionOwnershipError:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="resource is not available") from None
    except DeletionNotAllowedError:
        raise AppException(status_code=409, code=ErrorCode.PRECONDITION_NOT_MET, message="job cannot be deleted in its current state") from None
    return success_response(
        ResourceDeletionResponse(
            resource_type=result.resource_type,
            resource_id=result.resource_id,
            deleted=result.deleted,
        ).model_dump(mode="json")
    )
