"""Application service for the S-02 HR Job upload boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from uuid import UUID

from app.infrastructure.storage.local import LocalObjectStorage
from app.repositories.async_task_repository import (
    AsyncTaskRepository,
    JobTaskPreconditionError,
)
from app.repositories.job_upload_repository import JobUploadRepository
from app.schemas.job_upload import JobUploadResponse, JobUploadResult

MAX_FILE_SIZE = 10_000_000
ALLOWED_JOB_FILE_TYPES = {
    "md": "text/markdown",
}


class InvalidJobUploadError(Exception):
    """The caller supplied an invalid JD file."""


@dataclass(frozen=True)
class JobUploadInput:
    content: bytes
    filename: str | None
    declared_mime: str | None


class JobUploadService:
    """Coordinates per-file validation, storage, Job creation, and handoff."""

    def __init__(
        self,
        *,
        repository: JobUploadRepository,
        task_repository: AsyncTaskRepository,
        storage: LocalObjectStorage,
    ) -> None:
        self._repository = repository
        self._task_repository = task_repository
        self._storage = storage

    async def upload_many(
        self, *, hr_profile_id: UUID, uploads: list[JobUploadInput]
    ) -> JobUploadResponse:
        results: list[JobUploadResult] = []
        for index, upload in enumerate(uploads):
            results.append(
                await self._upload_one(
                    index=index,
                    hr_profile_id=hr_profile_id,
                    upload_input=upload,
                )
            )
        return JobUploadResponse(results=results)

    async def _upload_one(
        self,
        *,
        index: int,
        hr_profile_id: UUID,
        upload_input: JobUploadInput,
    ) -> JobUploadResult:
        try:
            validated = _validate_upload(
                upload_input.content,
                upload_input.filename,
                upload_input.declared_mime,
            )
        except InvalidJobUploadError:
            return JobUploadResult(index=index, outcome="failed", error_code="invalid_file")

        try:
            stored_upload = self._storage.put(validated.content)
        except Exception:
            return JobUploadResult(index=index, outcome="failed", error_code="storage_failed")

        created_file_object = False
        try:
            async with self._repository.transaction():
                existing = await self._repository.find_active_by_digest(
                    hr_profile_id=hr_profile_id,
                    content_sha256=stored_upload.content_sha256,
                )
                if existing is not None:
                    result = JobUploadResult(
                        index=index,
                        outcome="duplicate",
                        job_id=existing.id,
                        task_status="existing",
                    )
                else:
                    job, created_file_object = await self._repository.create_job(
                        hr_profile_id=hr_profile_id,
                        upload=stored_upload,
                        detected_mime_type=validated.mime_type,
                    )
                    await self._task_repository.create_or_get_queued_job_task(
                        hr_profile_id=hr_profile_id,
                        job_id=job.id,
                    )
                    result = JobUploadResult(
                        index=index,
                        outcome="created",
                        job_id=job.id,
                        task_status="queued",
                    )
        except JobTaskPreconditionError:
            self._storage.delete(stored_upload.storage_key)
            return JobUploadResult(index=index, outcome="failed", error_code="handoff_failed")
        except Exception:
            self._storage.delete(stored_upload.storage_key)
            return JobUploadResult(index=index, outcome="failed", error_code="persistence_failed")

        if not created_file_object:
            self._storage.delete(stored_upload.storage_key)
        return result


@dataclass(frozen=True)
class _ValidatedUpload:
    content: bytes
    file_type: str
    mime_type: str


def _validate_upload(
    content: bytes, filename: str | None, declared_mime: str | None
) -> _ValidatedUpload:
    if not content or len(content) > MAX_FILE_SIZE or not filename:
        raise InvalidJobUploadError
    extension = PurePath(filename).suffix.lower().lstrip(".")
    expected_mime = ALLOWED_JOB_FILE_TYPES.get(extension)
    if expected_mime is None or declared_mime not in {expected_mime, "application/octet-stream"}:
        raise InvalidJobUploadError
    if extension == "md":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidJobUploadError from exc
    return _ValidatedUpload(content=content, file_type=extension, mime_type=expected_mime)
