"""Candidate preparation application services without direct ORM access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from uuid import UUID, uuid5

from app.infrastructure.storage.local import LocalObjectStorage
from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.candidate_preparation_repository import (
    CandidatePreparationRepository,
)
from app.schemas.candidate_preparation import (
    CandidateDocumentListItem,
    CandidateDocumentListResponse,
    CandidateDocumentUploadResponse,
    CandidateDocumentUploadResult,
    ResumeCreated,
    ResumeListItem,
    ResumeListResponse,
)

MAX_FILE_SIZE = 10_000_000
DOCUMENT_IDEMPOTENCY_NAMESPACE = UUID("f2f9bdde-0a30-4b92-9f6f-0f5a5d8a5c1f")


class InvalidUploadError(Exception):
    """The caller supplied a disallowed or malformed upload."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ResumeAlreadyExistsError(Exception):
    """The current MVP permits only one resume upload per candidate."""


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
                if await self._repository.has_other_resume(
                    candidate_id=candidate_id, idempotency_key=idempotency_key
                ):
                    raise ResumeAlreadyExistsError
                resume, reused, used_new_file_object = await self._repository.create_resume(
                    candidate_id=candidate_id,
                    name=display_name,
                    upload=upload,
                    idempotency_key=idempotency_key,
                )
                if not reused:
                    await self._task_repository.create_or_get_queued_resume_task(
                        candidate_id=candidate_id,
                        resume_id=resume.id,
                    )
        except Exception:
            self._storage.delete(upload.storage_key)
            raise
        if not used_new_file_object:
            self._storage.delete(upload.storage_key)
        return ResumeCreated(
            resume_id=resume.id,
            parse_status=getattr(resume, "parse_status", "processing"),
        )

    async def upload_documents(
        self,
        *,
        candidate_id: UUID,
        uploads: list[tuple[bytes, str | None, str | None]],
        idempotency_key: UUID | None,
    ) -> CandidateDocumentUploadResponse:
        results: list[CandidateDocumentUploadResult] = []
        for index, (content, filename, declared_mime) in enumerate(uploads):
            results.append(
                await self._upload_one_document(
                    candidate_id=candidate_id,
                    content=content,
                    filename=filename,
                    declared_mime=declared_mime,
                    idempotency_key=_per_file_idempotency_key(idempotency_key, content, index),
                )
            )
        return CandidateDocumentUploadResponse(results=results)

    async def _upload_one_document(
        self,
        *,
        candidate_id: UUID,
        content: bytes,
        filename: str | None,
        declared_mime: str | None,
        idempotency_key: UUID | None,
    ) -> CandidateDocumentUploadResult:
        safe_filename = filename or ""
        try:
            validated = _validate_document_upload(content, filename, declared_mime)
        except InvalidUploadError as exc:
            return CandidateDocumentUploadResult(
                file_name=safe_filename,
                result="failed",
                upload_status="failed",
                failure_code=exc.code,  # type: ignore[arg-type]
            )

        try:
            upload = self._storage.put(validated.content)
            display_name = _display_name(None, filename, "document", validated.file_type)
            document, reused, used_new_file_object = await self._repository.create_document(
                candidate_id=candidate_id,
                name=display_name,
                file_type=validated.file_type,
                detected_mime_type=validated.mime_type,
                upload=upload,
                idempotency_key=idempotency_key,
            )
        except OSError:
            if "upload" in locals():
                _delete_transient_upload(self._storage, upload.storage_key)
            return CandidateDocumentUploadResult(
                file_name=safe_filename,
                result="failed",
                upload_status="failed",
                failure_code="storage_unavailable",
            )
        except Exception:
            if "upload" in locals():
                _delete_transient_upload(self._storage, upload.storage_key)
            return CandidateDocumentUploadResult(
                file_name=safe_filename,
                result="failed",
                upload_status="failed",
                failure_code="internal_error",
            )

        if not used_new_file_object:
            self._storage.delete(upload.storage_key)
        return CandidateDocumentUploadResult(
            file_name=safe_filename,
            result="duplicate" if reused else "created",
            candidate_document_id=document.id,
            file_type=document.file_type,
            upload_status="success",
            uploaded_at=document.created_at,
        )
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
        self, candidate_id: UUID, page: int, page_size: int
    ) -> CandidateDocumentListResponse:
        values, total = await self._repository.list_documents(
            candidate_id, page, page_size
        )
        return CandidateDocumentListResponse(
            list=[
                CandidateDocumentListItem(
                    candidate_document_id=value.id,
                    name=value.document_name,
                    file_type=value.file_type,
                    upload_status="success",
                    created_at=value.created_at,
                )
                for value in values
            ],
            total=total,
            page=page,
            page_size=page_size,
        )


def _delete_transient_upload(storage: LocalObjectStorage, storage_key: str) -> None:
    try:
        storage.delete(storage_key)
    except OSError:
        pass

def _display_name(value: str | None, filename: str | None, prefix: str, extension: str) -> str:
    selected = (value or filename or f"{prefix}-upload.{extension}").strip()
    if not 1 <= len(selected) <= 255:
        raise InvalidUploadError("unsupported_file")
    return selected


def _per_file_idempotency_key(
    batch_key: UUID | None, content: bytes, index: int
) -> UUID | None:
    if batch_key is None:
        return None
    import hashlib

    digest = hashlib.sha256(content).hexdigest()
    return uuid5(DOCUMENT_IDEMPOTENCY_NAMESPACE, f"{batch_key}:{index}:{digest}")


def _validate_upload(
    content: bytes, filename: str | None, declared_mime: str | None, allowed: dict[str, str]
) -> ValidatedUpload:
    if not content:
        raise InvalidUploadError("empty_file")
    if len(content) > MAX_FILE_SIZE:
        raise InvalidUploadError("file_too_large")
    if not filename:
        raise InvalidUploadError("unsupported_file")
    extension = PurePath(filename).suffix.lower().lstrip(".")
    expected_mime = allowed.get(extension)
    if expected_mime is None or declared_mime not in {expected_mime, "application/octet-stream"}:
        raise InvalidUploadError("unsupported_file")
    if extension == "pdf" and not content.startswith(b"%PDF-"):
        raise InvalidUploadError("unsupported_file")
    if extension in {"jpg", "jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise InvalidUploadError("unsupported_file")
    if extension == "png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise InvalidUploadError("unsupported_file")
    if extension == "md":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidUploadError("unsupported_file") from exc
    return ValidatedUpload(content=content, file_type=extension, mime_type=expected_mime)


def _validate_document_upload(
    content: bytes, filename: str | None, declared_mime: str | None
) -> ValidatedUpload:
    return _validate_upload(
        content,
        filename,
        declared_mime,
        {
            "pdf": "application/pdf",
            "md": "text/markdown",
            "jpg": "image/jpeg",
            "png": "image/png",
        },
    )
