"""Authenticated candidate-owned resume, document, and profile endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_candidate_preparation_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.repositories.candidate_preparation_repository import IdempotencyConflictError
from app.schemas.candidate_preparation import DocumentType
from app.schemas.response import success_response
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
    return success_response(
        value.model_dump(mode="json"),
        msg="上传成功",
        code=ErrorCode.UPLOAD_SUCCEEDED,
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
    return success_response(value.model_dump(mode="json"))


@candidate_preparation_router.post("/candidate_documents", status_code=status.HTTP_201_CREATED)
async def upload_candidate_document(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[CandidatePreparationService, Depends(get_candidate_preparation_service)],
    file: Annotated[UploadFile, File()],
    candidate_document_type: Annotated[DocumentType, Form()],
    name: Annotated[str | None, Form()] = None,
    idempotency_key: Annotated[UUID | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, object]:
    try:
        value = await service.upload_document(
            candidate_id=identity.candidate_id,
            content=await file.read(),
            filename=file.filename,
            declared_mime=file.content_type,
            name=name,
            document_type=candidate_document_type,
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
    return success_response(
        value.model_dump(mode="json"),
        msg="上传成功",
        code=ErrorCode.UPLOAD_SUCCEEDED,
    )


@candidate_preparation_router.get("/candidate_documents")
async def list_candidate_documents(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[CandidatePreparationService, Depends(get_candidate_preparation_service)],
    page: int = 1,
    page_size: int = 20,
    candidate_document_type: DocumentType | None = None,
) -> dict[str, object]:
    if page < 1 or not 1 <= page_size <= 100:
        raise AppException(
            status_code=400, code=ErrorCode.VALIDATION_ERROR, message="invalid pagination"
        )
    value = await service.list_documents(
        identity.candidate_id, page, page_size, candidate_document_type
    )
    return success_response(value.model_dump(mode="json"))
