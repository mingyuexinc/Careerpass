"""Candidate preparation application services without direct ORM access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from uuid import UUID

from app.infrastructure.storage.local import LocalObjectStorage
from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.candidate_preparation_repository import (
    CandidatePreparationRepository,
)
from app.schemas.candidate_preparation import (
    CandidateDocumentCreated,
    CandidateDocumentListItem,
    CandidateDocumentListResponse,
    ResumeCreated,
    ResumeListItem,
    ResumeListResponse,
)

MAX_FILE_SIZE = 10_000_000


class InvalidUploadError(Exception):
    """The caller supplied a disallowed or malformed upload."""


@dataclass(frozen=True)
class ValidatedUpload:
    content: bytes
    file_type: str
    mime_type: str


class CandidatePreparationService:
    """Coordinates validated uploads, opaque storage, and repository transactions."""

    def __init__(
        self,
        *,
        repository: CandidatePreparationRepository,
        task_repository: AsyncTaskRepository,
        storage: LocalObjectStorage,
    ) -> None:
        self._repository = repository
        self._task_repository = task_repository
        self._storage = storage

    async def upload_resume(
        self,
        *,
        candidate_id: UUID,
        content: bytes,
        filename: str | None,
        declared_mime: str | None,
        name: str | None,
        idempotency_key: UUID | None,
    ) -> ResumeCreated:
        validated = _validate_upload(content, filename, declared_mime, {"pdf": "application/pdf"})
        upload = self._storage.put(validated.content)
        display_name = _display_name(name, filename, "resume", "pdf")
        try:
            async with self._repository.transaction():
                resume, _, used_new_file_object = await self._repository.create_resume(
                    candidate_id=candidate_id,
                    name=display_name,
                    upload=upload,
                    idempotency_key=idempotency_key,
                )
                await self._task_repository.create_or_get_queued_resume_task(
                    candidate_id=candidate_id,
                    resume_id=resume.id,
                )
        except Exception:
            self._storage.delete(upload.storage_key)
            raise
        if not used_new_file_object:
            self._storage.delete(upload.storage_key)
        return ResumeCreated(resume_id=resume.id, parse_status="processing")

    async def upload_document(
        self,
        *,
        candidate_id: UUID,
        content: bytes,
        filename: str | None,
        declared_mime: str | None,
        name: str | None,
        document_type: str,
        idempotency_key: UUID | None,
    ) -> CandidateDocumentCreated:
        validated = _validate_upload(
            content,
            filename,
            declared_mime,
            {
                "pdf": "application/pdf",
                "md": "text/markdown",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
            },
        )
        upload = self._storage.put(validated.content)
        display_name = _display_name(name, filename, "document", validated.file_type)
        try:
            document, _, used_new_file_object = await self._repository.create_document(
                candidate_id=candidate_id,
                name=display_name,
                document_type=document_type,
                file_type=validated.file_type,
                detected_mime_type=validated.mime_type,
                upload=upload,
                idempotency_key=idempotency_key,
            )
        except Exception:
            self._storage.delete(upload.storage_key)
            raise
        if not used_new_file_object:
            self._storage.delete(upload.storage_key)
        return CandidateDocumentCreated(candidate_document_id=document.id)

    async def list_resumes(
        self, candidate_id: UUID, page: int, page_size: int
    ) -> ResumeListResponse:
        values, total = await self._repository.list_resumes(candidate_id, page, page_size)
        return ResumeListResponse(
            list=[
                ResumeListItem(
                    resume_id=value.id,
                    name=value.file_name,
                    created_at=value.created_at,
                    parse_status=value.parse_status,
                    failure_code=value.failure_code if value.parse_status == "failed" else None,
                )
                for value in values
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def list_documents(
        self, candidate_id: UUID, page: int, page_size: int, document_type: str | None
    ) -> CandidateDocumentListResponse:
        values, total = await self._repository.list_documents(
            candidate_id, page, page_size, document_type
        )
        return CandidateDocumentListResponse(
            list=[
                CandidateDocumentListItem(
                    candidate_document_id=value.id,
                    name=value.document_name,
                    type=value.document_type,
                    created_at=value.created_at,
                )
                for value in values
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

def _display_name(value: str | None, filename: str | None, prefix: str, extension: str) -> str:
    selected = (value or filename or f"{prefix}-upload.{extension}").strip()
    if not 1 <= len(selected) <= 255:
        raise InvalidUploadError
    return selected


def _validate_upload(
    content: bytes, filename: str | None, declared_mime: str | None, allowed: dict[str, str]
) -> ValidatedUpload:
    if not content or len(content) > MAX_FILE_SIZE or not filename:
        raise InvalidUploadError
    extension = PurePath(filename).suffix.lower().lstrip(".")
    expected_mime = allowed.get(extension)
    if expected_mime is None or declared_mime not in {expected_mime, "application/octet-stream"}:
        raise InvalidUploadError
    if extension == "pdf" and not content.startswith(b"%PDF-"):
        raise InvalidUploadError
    if extension in {"jpg", "jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise InvalidUploadError
    if extension == "md":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidUploadError from exc
    return ValidatedUpload(content=content, file_type=extension, mime_type=expected_mime)
