"""Repository boundary for S-03 JD tasks, inputs, snapshots, and ownership."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AsyncTaskRun,
    Job,
    ParsedJobDescriptionSnapshot,
    StoredFileObject,
)
from app.repositories.async_task_repository import ExecutionLease
from app.schemas.job_description import ParsedJobDescriptionFields


class JobDescriptionTaskPreconditionError(Exception):
    """The requested Job cannot safely receive or execute an S-03 task."""


class JobDescriptionStorageUnavailableError(Exception):
    """The registered JD object cannot be read through the controlled storage port."""


@dataclass(frozen=True)
class JobDescriptionTaskView:
    task: AsyncTaskRun
    job_id: UUID
    snapshot: ParsedJobDescriptionSnapshot | None


class JobDescriptionRepository:
    """Own all S-03 persistence and resource-ownership checks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        return self._session.begin()

    async def find_job_by_content_digest(
        self, *, hr_profile_id: UUID, content_sha256: str
    ) -> Job | None:
        statement = (
            select(Job)
            .join(StoredFileObject, Job.stored_file_object_id == StoredFileObject.id)
            .where(
                Job.hr_profile_id == hr_profile_id,
                Job.deleted_at.is_(None),
                StoredFileObject.content_sha256 == content_sha256,
                StoredFileObject.status == "ready",
            )
            .order_by(Job.created_at, Job.id)
        )
        return await self._session.scalar(statement)

    async def create_or_get_queued_task(
        self,
        *,
        hr_profile_id: UUID,
        job_id: UUID,
        task_version: str = "v1",
    ) -> tuple[AsyncTaskRun, bool]:
        job = await self._locked_job_with_file(job_id=job_id, hr_profile_id=hr_profile_id)
        if job is None:
            raise JobDescriptionTaskPreconditionError
        existing_tasks = list(
            (
                await self._session.scalars(
                    select(AsyncTaskRun)
                    .where(
                        AsyncTaskRun.task_type == "job_jd_parse",
                        AsyncTaskRun.resource_type == "job",
                        AsyncTaskRun.resource_id == job_id,
                        AsyncTaskRun.task_version == task_version,
                    )
                    .order_by(desc(AsyncTaskRun.task_generation), desc(AsyncTaskRun.created_at))
                    .with_for_update()
                )
            ).all()
        )
        latest = existing_tasks[0] if existing_tasks else None
        if latest is not None and latest.status != "failed":
            return latest, False

        generation = (latest.task_generation if latest is not None else 0) + 1
        idempotency_key = f"job_jd_parse:{job_id}:{task_version}:{generation}"
        statement = (
            postgres_insert(AsyncTaskRun)
            .values(
                task_type="job_jd_parse",
                resource_type="job",
                resource_id=job_id,
                idempotency_key=idempotency_key,
                task_version=task_version,
                task_generation=generation,
                status="queued",
            )
            .on_conflict_do_nothing(index_elements=[AsyncTaskRun.idempotency_key])
        )
        await self._session.execute(statement)
        task = await self._session.scalar(
            select(AsyncTaskRun)
            .where(AsyncTaskRun.idempotency_key == idempotency_key)
            .with_for_update()
        )
        if task is None:
            raise JobDescriptionTaskPreconditionError
        return task, task.id not in {item.id for item in existing_tasks}

    async def get_task_for_hr(
        self, *, task_id: UUID, hr_profile_id: UUID
    ) -> JobDescriptionTaskView | None:
        row = (
            await self._session.execute(
                select(AsyncTaskRun, Job)
                .join(Job, AsyncTaskRun.resource_id == Job.id)
                .where(
                    AsyncTaskRun.id == task_id,
                    AsyncTaskRun.task_type == "job_jd_parse",
                    AsyncTaskRun.resource_type == "job",
                    Job.hr_profile_id == hr_profile_id,
                )
            )
        ).one_or_none()
        if row is None:
            return None
        task, job = row
        snapshot = await self._session.scalar(
            select(ParsedJobDescriptionSnapshot).where(
                ParsedJobDescriptionSnapshot.job_id == job.id
            )
        )
        return JobDescriptionTaskView(task=task, job_id=job.id, snapshot=snapshot)

    async def read_for_processing(
        self,
        *,
        job_id: UUID,
        hr_profile_id: UUID,
        storage_key_reader: Callable[[str], bytes],
    ) -> bytes:
        row = await self._locked_job_with_file(job_id=job_id, hr_profile_id=hr_profile_id)
        if row is None:
            raise JobDescriptionStorageUnavailableError
        _, file_object = row
        try:
            content = storage_key_reader(file_object.storage_key)
            hashlib.sha256(content).hexdigest()
            content.decode("utf-8")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise JobDescriptionStorageUnavailableError from exc
        return content

    async def read_for_worker(
        self, *, job_id: UUID, storage_key_reader: Callable[[str], bytes]
    ) -> bytes:
        row = (
            await self._session.execute(
                select(Job, StoredFileObject)
                .join(StoredFileObject, Job.stored_file_object_id == StoredFileObject.id)
                .where(
                    Job.id == job_id,
                    Job.deleted_at.is_(None),
                    StoredFileObject.status == "ready",
                )
            )
        ).one_or_none()
        if row is None:
            raise JobDescriptionStorageUnavailableError
        _, file_object = row
        try:
            content = storage_key_reader(file_object.storage_key)
            content.decode("utf-8")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise JobDescriptionStorageUnavailableError from exc
        return content

    async def complete_for_execution(
        self,
        *,
        lease: ExecutionLease,
        fields: ParsedJobDescriptionFields,
        raw_sections: list[dict[str, object]],
        schema_version: str,
    ) -> bool:
        async with self._session.begin():
            task = await self._locked_running_task(lease)
            if task is None:
                return False
            job = await self._session.scalar(
                select(Job)
                .where(Job.id == lease.resource_id, Job.deleted_at.is_(None))
                .with_for_update()
            )
            if job is None:
                return False
            snapshot = await self._session.scalar(
                select(ParsedJobDescriptionSnapshot)
                .where(ParsedJobDescriptionSnapshot.job_id == job.id)
                .with_for_update()
            )
            if snapshot is None:
                snapshot = ParsedJobDescriptionSnapshot(
                    job_id=job.id,
                    schema_version=schema_version,
                    fields=fields.model_dump(mode="json"),
                    raw_sections=raw_sections,
                )
                self._session.add(snapshot)
            else:
                snapshot.schema_version = schema_version
                snapshot.fields = fields.model_dump(mode="json")
                snapshot.raw_sections = raw_sections
                snapshot.created_at = datetime.now(UTC)
            task.status = "succeeded"
            task.failure_code = None
            task.failure_semantics = None
            task.failure_reason = None
            task.missing_core_fields = None
            task.finished_at = datetime.now(UTC)
            task.execution_token = None
            task.execution_lease_expires_at = None
        return True

    async def fail_for_execution(
        self,
        *,
        lease: ExecutionLease,
        failure_semantics: str,
        failure_reason: str,
        missing_core_fields: list[str] | None = None,
    ) -> bool:
        async with self._session.begin():
            task = await self._locked_running_task(lease)
            if task is None:
                return False
            task.status = "failed"
            task.failure_code = None
            task.failure_semantics = failure_semantics
            task.failure_reason = failure_reason
            task.missing_core_fields = missing_core_fields
            task.finished_at = datetime.now(UTC)
            task.execution_token = None
            task.execution_lease_expires_at = None
        return True

    async def _locked_job_with_file(
        self, *, job_id: UUID, hr_profile_id: UUID
    ) -> tuple[Job, StoredFileObject] | None:
        row = (
            await self._session.execute(
                select(Job, StoredFileObject)
                .join(StoredFileObject, Job.stored_file_object_id == StoredFileObject.id)
                .where(
                    Job.id == job_id,
                    Job.hr_profile_id == hr_profile_id,
                    Job.deleted_at.is_(None),
                    StoredFileObject.status == "ready",
                )
                .with_for_update()
            )
        ).one_or_none()
        return row

    async def _locked_running_task(self, lease: ExecutionLease) -> AsyncTaskRun | None:
        return await self._session.scalar(
            select(AsyncTaskRun)
            .where(
                AsyncTaskRun.id == lease.task_run_id,
                AsyncTaskRun.task_type == "job_jd_parse",
                AsyncTaskRun.resource_type == "job",
                AsyncTaskRun.resource_id == lease.resource_id,
                AsyncTaskRun.status == "running",
                AsyncTaskRun.execution_token == lease.execution_token,
            )
            .with_for_update()
        )
