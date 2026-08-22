"""Application service for S-03 submission and result queries."""

from __future__ import annotations

import hashlib
from uuid import UUID

from app.infrastructure.storage.controlled import ControlledJobDescriptionStorage
from app.repositories.job_description_repository import (
    JobDescriptionRepository,
    JobDescriptionRetryNotAllowedError,
    JobDescriptionTaskPreconditionError,
)
from app.schemas.job_description import (
    JobDescriptionParseResult,
    JobDescriptionParseRetryData,
    JobDescriptionParseSubmitData,
)


class JobDescriptionInputUnavailableError(Exception):
    """The internal verification input is not within the controlled registered scope."""


class JobDescriptionService:
    """Coordinate controlled path validation and repository-backed task operations."""

    def __init__(
        self,
        *,
        repository: JobDescriptionRepository,
        storage: ControlledJobDescriptionStorage,
    ) -> None:
        self._repository = repository
        self._storage = storage

    async def submit(
        self, *, hr_profile_id: UUID, local_path: str
    ) -> JobDescriptionParseSubmitData:
        try:
            content = self._storage.read(local_path)
        except (OSError, ValueError):
            raise JobDescriptionInputUnavailableError from None
        digest = hashlib.sha256(content).hexdigest()
        async with self._repository.transaction():
            job = await self._repository.find_job_by_content_digest(
                hr_profile_id=hr_profile_id,
                content_sha256=digest,
            )
            if job is None:
                raise JobDescriptionInputUnavailableError
            try:
                task, _ = await self._repository.create_or_get_queued_task(
                    hr_profile_id=hr_profile_id,
                    job_id=job.id,
                )
            except JobDescriptionTaskPreconditionError:
                raise JobDescriptionInputUnavailableError from None
        return JobDescriptionParseSubmitData(task_id=task.id, status=task.status)

    async def get_result(
        self, *, hr_profile_id: UUID, task_id: UUID
    ) -> JobDescriptionParseResult | None:
        view = await self._repository.get_task_for_hr(
            task_id=task_id,
            hr_profile_id=hr_profile_id,
        )
        if view is None:
            return None
        task = view.task
        succeeded = task.status == "succeeded" and view.snapshot is not None
        snapshot = view.snapshot if succeeded else None
        result = JobDescriptionParseResult(
            task_id=task.id,
            job_id=view.job_id,
            status=task.status,
            parse_status=task.status,
            matching_status="matching_ready" if succeeded else None,
            snapshot_id=snapshot.id if snapshot is not None else None,
            schema_version=snapshot.schema_version if snapshot is not None else None,
            fields=snapshot.fields if snapshot is not None else None,
            failure_semantics=task.failure_semantics,
            failure_reason=task.failure_reason,
            missing_core_fields=task.missing_core_fields or [],
        )
        return result

    async def retry_failed_job(
        self, *, hr_profile_id: UUID, job_id: UUID
    ) -> JobDescriptionParseRetryData:
        async with self._repository.transaction():
            try:
                task, _ = await self._repository.retry_failed_task(
                    hr_profile_id=hr_profile_id,
                    job_id=job_id,
                )
            except (JobDescriptionRetryNotAllowedError, JobDescriptionTaskPreconditionError):
                raise
        return JobDescriptionParseRetryData(
            job_id=job_id,
            task_id=task.id,
            status=task.status,
        )
