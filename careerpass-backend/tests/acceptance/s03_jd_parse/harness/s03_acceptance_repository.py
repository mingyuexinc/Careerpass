"""Persistence boundary used by the S-03 internal-capability acceptance harness."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AsyncTaskRun,
    HrProfile,
    Job,
    ParsedJobDescriptionSnapshot,
    StoredFileObject,
    User,
    UserRole,
)
from app.infrastructure.storage.local import StoredUpload
from app.repositories.job_upload_repository import JobUploadRepository


@dataclass(frozen=True)
class ControlledHrIdentity:
    """The pre-existing seeded HR identity used by acceptance setup."""

    user_id: UUID
    hr_profile_id: UUID


@dataclass(frozen=True)
class CreatedJob:
    """Identifiers needed for assertions and deterministic cleanup."""

    job_id: UUID
    file_object_id: UUID
    storage_key: str
    created_file_object: bool


class S03AcceptanceRepository:
    """Keep setup, inspection, and cleanup queries behind a test repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_controlled_hr(self, username: str) -> ControlledHrIdentity:
        statement = (
            select(User.id, HrProfile.id)
            .join(HrProfile, HrProfile.user_id == User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .where(User.username == username, UserRole.role == "hr")
            .distinct()
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            raise AssertionError(f"controlled HR identity unavailable: {username}")
        user_id, hr_profile_id = row
        return ControlledHrIdentity(user_id=user_id, hr_profile_id=hr_profile_id)

    async def create_job(
        self,
        *,
        hr_profile_id: UUID,
        upload: StoredUpload,
        detected_mime_type: str,
    ) -> CreatedJob:
        uploader = JobUploadRepository(self._session)
        job, created_file_object = await uploader.create_job(
            hr_profile_id=hr_profile_id,
            upload=upload,
            detected_mime_type=detected_mime_type,
        )
        file_object = await self._session.get(StoredFileObject, job.stored_file_object_id)
        if file_object is None or file_object.status != "ready":
            raise AssertionError("acceptance Job did not receive a ready StoredFileObject")
        return CreatedJob(
            job_id=job.id,
            file_object_id=file_object.id,
            storage_key=file_object.storage_key,
            created_file_object=created_file_object,
        )

    async def inspect_result(
        self,
        *,
        hr_profile_id: UUID,
        job_id: UUID,
        task_id: UUID,
    ) -> dict[str, object]:
        job = await self._session.scalar(
            select(Job).where(Job.id == job_id, Job.hr_profile_id == hr_profile_id)
        )
        if job is None:
            raise AssertionError("S-03 Job ownership check failed")
        file_object = await self._session.get(StoredFileObject, job.stored_file_object_id)
        task = await self._session.get(AsyncTaskRun, task_id)
        snapshot = await self._session.scalar(
            select(ParsedJobDescriptionSnapshot).where(
                ParsedJobDescriptionSnapshot.job_id == job_id
            )
        )
        task_count = await self._session.scalar(
            select(func.count(AsyncTaskRun.id)).where(
                AsyncTaskRun.task_type == "job_jd_parse",
                AsyncTaskRun.resource_type == "job",
                AsyncTaskRun.resource_id == job_id,
            )
        )
        snapshot_count = await self._session.scalar(
            select(func.count(ParsedJobDescriptionSnapshot.id)).where(
                ParsedJobDescriptionSnapshot.job_id == job_id
            )
        )
        return {
            "job_id": str(job.id),
            "hr_profile_id": str(job.hr_profile_id),
            "file_object_status": file_object.status if file_object else None,
            "task_id": str(task.id) if task else None,
            "task_status": task.status if task else None,
            "task_generation": task.task_generation if task else None,
            "snapshot_id": str(snapshot.id) if snapshot else None,
            "schema_version": snapshot.schema_version if snapshot else None,
            "fields": snapshot.fields if snapshot else None,
            "raw_sections": snapshot.raw_sections if snapshot else None,
            "task_count": int(task_count or 0),
            "snapshot_count": int(snapshot_count or 0),
            "handoff_ready": bool(
                task is not None
                and task.status == "succeeded"
                and snapshot is not None
                and snapshot.schema_version == "v1"
            ),
        }

    async def cleanup(
        self, *, job_id: UUID, file_object_id: UUID, delete_file_object: bool = True
    ) -> None:
        """Delete only resources created by this scenario after the task is terminal."""
        task_statuses = list(
            (
                await self._session.scalars(
                    select(AsyncTaskRun.status).where(AsyncTaskRun.resource_id == job_id)
                )
            ).all()
        )
        if any(status in {"queued", "running"} for status in task_statuses):
            raise RuntimeError("cannot clean an active S-03 task")
        await self._session.rollback()
        async with self._session.begin():
            await self._session.execute(
                delete(ParsedJobDescriptionSnapshot).where(
                    ParsedJobDescriptionSnapshot.job_id == job_id
                )
            )
            await self._session.execute(
                delete(AsyncTaskRun).where(AsyncTaskRun.resource_id == job_id)
            )
            await self._session.execute(delete(Job).where(Job.id == job_id))
            if delete_file_object:
                await self._session.execute(
                    delete(StoredFileObject).where(StoredFileObject.id == file_object_id)
                )
