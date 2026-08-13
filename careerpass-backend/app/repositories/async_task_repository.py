"""Repository operations for durable async-task dispatch and execution leases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import AsyncTaskRun, Job, Resume, StoredFileObject


@dataclass(frozen=True)
class DispatchLease:
    """A task publication lease owned by one Dispatcher iteration."""

    task_run_id: UUID
    task_type: str
    celery_task_id: str
    dispatch_token: UUID


@dataclass(frozen=True)
class ExecutionLease:
    """A task execution lease; its token must guard every later state write."""

    task_run_id: UUID
    task_type: str
    resource_type: str
    resource_id: UUID
    execution_token: UUID


class ResumeTaskPreconditionError(Exception):
    """Raised when a resume cannot safely receive a parsing task."""


class JobTaskPreconditionError(Exception):
    """Raised when a job cannot safely receive a parsing task."""


class AsyncTaskRepository:
    """The only persistence boundary for dispatcher and worker task state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_or_get_queued_resume_task(
        self,
        *,
        candidate_id: UUID,
        resume_id: UUID,
        task_version: Literal["v1"] = "v1",
    ) -> tuple[AsyncTaskRun, bool]:
        """Create or reuse the one durable queued task for a candidate-owned resume."""
        resource = await self._session.execute(
            select(Resume, StoredFileObject)
            .join(StoredFileObject, Resume.stored_file_object_id == StoredFileObject.id)
            .where(Resume.id == resume_id, Resume.candidate_id == candidate_id)
            .with_for_update()
        )
        resource_row = resource.one_or_none()
        if resource_row is None:
            raise ResumeTaskPreconditionError
        resume, file_object = resource_row
        idempotency_key = f"resume_parse:{resume_id}:{task_version}"

        existing = await self._session.scalar(
            select(AsyncTaskRun)
            .where(AsyncTaskRun.idempotency_key == idempotency_key)
            .with_for_update()
        )
        if existing is not None:
            if (
                existing.task_type != "resume_parse"
                or existing.resource_type != "resume"
                or existing.resource_id != resume_id
                or existing.task_version != task_version
            ):
                raise ResumeTaskPreconditionError
            return existing, False

        if file_object.status != "ready" or resume.parse_status != "processing":
            raise ResumeTaskPreconditionError

        statement = (
            postgres_insert(AsyncTaskRun)
            .values(
                task_type="resume_parse",
                resource_type="resume",
                resource_id=resume_id,
                idempotency_key=idempotency_key,
                task_version=task_version,
                status="queued",
            )
            .on_conflict_do_nothing(index_elements=[AsyncTaskRun.idempotency_key])
        )
        result = await self._session.execute(statement)
        task = await self._session.scalar(
            select(AsyncTaskRun)
            .where(AsyncTaskRun.idempotency_key == idempotency_key)
            .with_for_update()
        )
        if task is None:
            raise ResumeTaskPreconditionError
        return task, result.rowcount == 1

    async def create_or_get_queued_job_task(
        self,
        *,
        hr_profile_id: UUID,
        job_id: UUID,
        task_version: str = "v1",
    ) -> tuple[AsyncTaskRun, bool]:
        """Create or reuse the durable queued task handed off by S-02."""
        resource = await self._session.execute(
            select(Job, StoredFileObject)
            .join(StoredFileObject, Job.stored_file_object_id == StoredFileObject.id)
            .where(
                Job.id == job_id,
                Job.hr_profile_id == hr_profile_id,
                Job.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if resource.one_or_none() is None:
            raise JobTaskPreconditionError

        idempotency_key = f"job_jd_parse:{job_id}:{task_version}"
        existing = await self._session.scalar(
            select(AsyncTaskRun)
            .where(AsyncTaskRun.idempotency_key == idempotency_key)
            .with_for_update()
        )
        if existing is not None:
            if (
                existing.task_type != "job_jd_parse"
                or existing.resource_type != "job"
                or existing.resource_id != job_id
                or existing.task_version != task_version
            ):
                raise JobTaskPreconditionError
            return existing, False

        statement = (
            postgres_insert(AsyncTaskRun)
            .values(
                task_type="job_jd_parse",
                resource_type="job",
                resource_id=job_id,
                idempotency_key=idempotency_key,
                task_version=task_version,
                status="queued",
            )
            .on_conflict_do_nothing(index_elements=[AsyncTaskRun.idempotency_key])
        )
        result = await self._session.execute(statement)
        task = await self._session.scalar(
            select(AsyncTaskRun)
            .where(AsyncTaskRun.idempotency_key == idempotency_key)
            .with_for_update()
        )
        if task is None:
            raise JobTaskPreconditionError
        return task, result.rowcount == 1

    async def claim_dispatch_batch(
        self, *, batch_size: int, lease_seconds: int
    ) -> list[DispatchLease]:
        """Claim unpublished or interrupted publications using row locks."""
        now = datetime.now(UTC)
        eligible = and_(
            AsyncTaskRun.status == "queued",
            AsyncTaskRun.dispatched_at.is_(None),
            or_(
                AsyncTaskRun.dispatch_token.is_(None),
                AsyncTaskRun.dispatch_lease_expires_at <= now,
            ),
        )
        async with self._session.begin():
            statement = (
                select(AsyncTaskRun)
                .where(eligible)
                .order_by(AsyncTaskRun.created_at, AsyncTaskRun.id)
                .with_for_update(skip_locked=True)
                .limit(batch_size)
            )
            tasks = list((await self._session.scalars(statement)).all())
            leases: list[DispatchLease] = []
            for task in tasks:
                celery_task_id = task.celery_task_id or str(uuid4())
                dispatch_token = uuid4()
                task.celery_task_id = celery_task_id
                task.dispatch_token = dispatch_token
                task.dispatch_lease_expires_at = now + timedelta(seconds=lease_seconds)
                leases.append(
                    DispatchLease(
                        task_run_id=task.id,
                        task_type=task.task_type,
                        celery_task_id=celery_task_id,
                        dispatch_token=dispatch_token,
                    )
                )
        return leases

    async def confirm_dispatch(self, *, task_run_id: UUID, dispatch_token: UUID) -> bool:
        """Mark publication complete only for the Dispatcher that owns its lease."""
        async with self._session.begin():
            task = await self._locked_task(task_run_id)
            if (
                task is None
                or task.status != "queued"
                or task.dispatch_token != dispatch_token
            ):
                return False
            task.dispatched_at = datetime.now(UTC)
            task.dispatch_token = None
            task.dispatch_lease_expires_at = None
        return True

    async def release_dispatch(self, *, task_run_id: UUID, dispatch_token: UUID) -> bool:
        """Release a failed publication attempt without changing business task state."""
        async with self._session.begin():
            task = await self._locked_task(task_run_id)
            if (
                task is None
                or task.status != "queued"
                or task.dispatch_token != dispatch_token
            ):
                return False
            task.dispatch_token = None
            task.dispatch_lease_expires_at = None
        return True

    async def claim_execution(
        self, *, task_run_id: UUID, lease_seconds: int
    ) -> ExecutionLease | None:
        """Atomically claim a queued task or a task whose previous lease expired."""
        now = datetime.now(UTC)
        async with self._session.begin():
            task = await self._locked_task(task_run_id)
            if task is None or not _execution_claimable(task, now):
                return None
            token = uuid4()
            task.status = "running"
            task.execution_token = token
            task.started_at = now
            task.execution_lease_expires_at = now + timedelta(seconds=lease_seconds)
            return ExecutionLease(
                task_run_id=task.id,
                task_type=task.task_type,
                resource_type=task.resource_type,
                resource_id=task.resource_id,
                execution_token=token,
            )

    async def release_execution_for_retry(
        self, *, task_run_id: UUID, execution_token: UUID
    ) -> bool:
        """Return a retryable task to queued only when its current lease still matches."""
        async with self._session.begin():
            task = await self._locked_task(task_run_id)
            if task is None or task.status != "running" or task.execution_token != execution_token:
                return False
            task.status = "queued"
            task.execution_token = None
            task.execution_lease_expires_at = None
            task.started_at = None
            task.dispatched_at = None
        return True

    async def fail_execution_after_timeout(self, *, task_run_id: UUID) -> bool:
        """Close the current, non-expired lease when Celery interrupts the task."""
        now = datetime.now(UTC)
        async with self._session.begin():
            task = await self._locked_task(task_run_id)
            if (
                task is None
                or task.status != "running"
                or task.execution_lease_expires_at is None
                or task.execution_lease_expires_at <= now
            ):
                return False
            task.status = "failed"
            task.failure_code = "internal_error"
            task.finished_at = now
            task.execution_token = None
            task.execution_lease_expires_at = None
            if task.resource_type == "resume":
                resume = await self._session.get(Resume, task.resource_id, with_for_update=True)
                if resume is not None and resume.parse_status == "processing":
                    resume.parse_status = "failed"
                    resume.failure_code = "internal_error"
        return True

    async def fail_stalled_tasks(self, *, stalled_after_seconds: int = 600) -> int:
        """Fail only expired leases that remained running past the conservative timeout."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=stalled_after_seconds)
        async with self._session.begin():
            statement = (
                select(AsyncTaskRun)
                .where(
                    AsyncTaskRun.status == "running",
                    AsyncTaskRun.started_at <= cutoff,
                    AsyncTaskRun.execution_lease_expires_at <= now,
                )
                .with_for_update(skip_locked=True)
            )
            tasks = list((await self._session.scalars(statement)).all())
            for task in tasks:
                task.status = "failed"
                task.failure_code = "internal_error"
                task.finished_at = now
                task.execution_token = None
                task.execution_lease_expires_at = None
                if task.resource_type == "resume":
                    resume = await self._session.get(Resume, task.resource_id, with_for_update=True)
                    if resume is not None and resume.parse_status == "processing":
                        resume.parse_status = "failed"
                        resume.failure_code = "internal_error"
        return len(tasks)

    async def _locked_task(self, task_run_id: UUID) -> AsyncTaskRun | None:
        statement = select(AsyncTaskRun).where(AsyncTaskRun.id == task_run_id).with_for_update()
        return await self._session.scalar(statement)


def _execution_claimable(task: AsyncTaskRun, now: datetime) -> bool:
    return task.status == "queued" or (
        task.status == "running"
        and task.execution_lease_expires_at is not None
        and task.execution_lease_expires_at <= now
    )
