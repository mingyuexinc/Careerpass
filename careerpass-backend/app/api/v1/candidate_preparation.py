"""Authenticated candidate-owned resume, document, and profile endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import (
    get_business_resource_deletion_service,
    get_candidate_preparation_service,
)
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.repositories.async_task_repository import ResumeTaskPreconditionError
from app.repositories.business_resource_deletion_repository import (
    DeletionNotAllowedError,
    DeletionOwnershipError,
    DeletionResourceNotFoundError,
)
from app.repositories.candidate_preparation_repository import IdempotencyConflictError
from app.schemas.business_resource_deletion import ResourceDeletionResponse
from app.schemas.response import success_response
from app.services.business_resource_deletion_service import BusinessResourceDeletionService
from app.services.candidate_preparation_service import (
    CandidatePreparationService,
    InvalidUploadError,
)

candidate_preparation_router = APIRouter(tags=["candidate-preparation"])


@candidate_preparation_router.post("/resumes", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[CandidatePreparationService, Depends(get_candidate_preparation_service)],
    file: Annotated[UploadFile, File()],
    name: Annotated[str | None, Form()] = None,
    idempotency_key: Annotated[UUID | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, object]:
    try:
        value = await service.upload_resume(
            candidate_id=identity.candidate_id,
            content=await file.read(),
            filename=file.filename,
            declared_mime=file.content_type,
            name=name,
            idempotency_key=idempotency_key,
        )
    except InvalidUploadError:
        raise AppException(
            status_code=400, code=ErrorCode.VALIDATION_ERROR, message="invalid upload"
        ) from None
    except IdempotencyConflictError:
        raise AppException(
            status_code=409, code=ErrorCode.CONFLICT, message="idempotency key conflict"
        ) from None
    except ResumeTaskPreconditionError:
        raise AppException(
            status_code=409,
            code=ErrorCode.PRECONDITION_NOT_MET,
            message="resume is not ready for parsing",
        ) from None
    return success_response(
        value.model_dump(mode="json"),
        msg="上传已受理，正在解析简历",
        code=ErrorCode.UPLOAD_ACCEPTED,
    )


@candidate_preparation_router.get("/resumes")
async def list_resumes(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[CandidatePreparationService, Depends(get_candidate_preparation_service)],
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    if page < 1 or not 1 <= page_size <= 100:
        raise AppException(
            status_code=400, code=ErrorCode.VALIDATION_ERROR, message="invalid pagination"
        )
    value = await service.list_resumes(identity.candidate_id, page, page_size)
    return success_response(value.model_dump(mode="json", exclude_none=True))


@candidate_preparation_router.post("/candidate_documents", status_code=status.HTTP_200_OK)
async def upload_candidate_document(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[CandidatePreparationService, Depends(get_candidate_preparation_service)],
    files: Annotated[list[UploadFile], File()],
    idempotency_key: Annotated[UUID | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, object]:
    if not files:
        raise AppException(
            status_code=400, code=ErrorCode.VALIDATION_ERROR, message="at least one file is required"
        )
    value = await service.upload_documents(
        candidate_id=identity.candidate_id,
        uploads=[(await file.read(), file.filename, file.content_type) for file in files],
        idempotency_key=idempotency_key,
    )
    return success_response(
        value.model_dump(mode="json"),
        msg="其它资料已就绪。",
        code=ErrorCode.SUCCESS,
    )


@candidate_preparation_router.get("/candidate_documents")
async def list_candidate_documents(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[CandidatePreparationService, Depends(get_candidate_preparation_service)],
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    if page < 1 or not 1 <= page_size <= 100:
        raise AppException(
            status_code=400, code=ErrorCode.VALIDATION_ERROR, message="invalid pagination"
        )
    value = await service.list_documents(identity.candidate_id, page, page_size)
    return success_response(value.model_dump(mode="json"))


@candidate_preparation_router.delete("/resumes/{resume_id}")
async def delete_resume(
    resume_id: UUID,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[BusinessResourceDeletionService, Depends(get_business_resource_deletion_service)],
) -> dict[str, object]:
    if identity.active_role != "candidate" or identity.candidate_id is None:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="Candidate identity required")
    try:
        result = await service.delete_resume(
            candidate_id=identity.candidate_id,
            resume_id=resume_id,
            actor_user_id=identity.user_id,
            actor_role=identity.active_role,
        )
    except DeletionResourceNotFoundError:
        raise AppException(status_code=404, code=ErrorCode.NOT_FOUND, message="resource not found") from None
    except DeletionOwnershipError:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="resource is not available") from None
    except DeletionNotAllowedError:
        raise AppException(status_code=409, code=ErrorCode.PRECONDITION_NOT_MET, message="resume cannot be deleted in its current state") from None
    return success_response(
        ResourceDeletionResponse(
            resource_type=result.resource_type,
            resource_id=result.resource_id,
            deleted=result.deleted,
        ).model_dump(mode="json")
    )


@candidate_preparation_router.delete("/candidate_documents/{document_id}")
async def delete_candidate_document(
    document_id: UUID,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[BusinessResourceDeletionService, Depends(get_business_resource_deletion_service)],
) -> dict[str, object]:
    if identity.active_role != "candidate" or identity.candidate_id is None:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="Candidate identity required")
    try:
        result = await service.delete_candidate_document(
            candidate_id=identity.candidate_id,
            document_id=document_id,
            actor_user_id=identity.user_id,
            actor_role=identity.active_role,
        )
    except DeletionResourceNotFoundError:
        raise AppException(status_code=404, code=ErrorCode.NOT_FOUND, message="resource not found") from None
    except DeletionOwnershipError:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="resource is not available") from None
    return success_response(
        ResourceDeletionResponse(
            resource_type=result.resource_type,
            resource_id=result.resource_id,
            deleted=result.deleted,
        ).model_dump(mode="json")
    )
