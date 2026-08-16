"""Repository operations for the internal object-directory lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import CandidateDocument, Job, Resume, StoredFileObject


@dataclass(frozen=True)
class CleanupClaim:
    """An unreferenced object exclusively claimed for physical deletion."""

    object_id: UUID
    storage_key: str
    previous_status: str


class ObjectStorageRepository:
    """Own transactional state transitions for stored-file cleanup."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_expired_unreferenced(
        self, *, older_than: datetime, limit: int
    ) -> list[CleanupClaim]:
        async with self._session.begin():
            has_resume = exists(select(1).where(Resume.stored_file_object_id == StoredFileObject.id))
            has_document = exists(
                select(1).where(CandidateDocument.stored_file_object_id == StoredFileObject.id)
            )
            has_active_job = exists(
                select(1).where(
                    Job.stored_file_object_id == StoredFileObject.id,
                    Job.deleted_at.is_(None),
                )
            )
            statement = (
                select(StoredFileObject)
                .where(
                    StoredFileObject.status.in_(("writing", "ready", "deleting")),
                    StoredFileObject.updated_at < older_than,
                    ~has_resume,
                    ~has_document,
                    ~has_active_job,
                )
                .order_by(StoredFileObject.updated_at, StoredFileObject.id)
                .with_for_update(skip_locked=True)
                .limit(limit)
            )
            values = list((await self._session.scalars(statement)).all())
            claims = [
                CleanupClaim(
                    object_id=value.id,
                    storage_key=value.storage_key,
                    previous_status=value.status,
                )
                for value in values
            ]
            for value in values:
                value.status = "deleting"
        return claims

    async def finalize_deletion(self, object_id: UUID) -> bool:
        """Delete only an unreferenced object still held in the deleting state."""
        async with self._session.begin():
            value = await self._session.get(StoredFileObject, object_id, with_for_update=True)
            if value is None or value.status != "deleting" or await self._has_reference(object_id):
                return False
            await self._session.delete(value)
        return True

    async def restore_after_delete_failure(self, claim: CleanupClaim) -> None:
        """Return a failed physical deletion to its retryable pre-claim state."""
        async with self._session.begin():
            value = await self._session.get(StoredFileObject, claim.object_id, with_for_update=True)
            if value is not None and value.status == "deleting":
                value.status = claim.previous_status

    async def _has_reference(self, object_id: UUID) -> bool:
        active_job_exists = await self._session.scalar(
            select(
                exists(
                    select(1).where(
                        Job.stored_file_object_id == object_id,
                        Job.deleted_at.is_(None),
                    )
                )
            )
        )
        if active_job_exists:
            return True
        resume_exists = await self._session.scalar(
            select(exists(select(1).where(Resume.stored_file_object_id == object_id)))
        )
        if resume_exists:
            return True
        return bool(
            await self._session.scalar(
                select(exists(select(1).where(CandidateDocument.stored_file_object_id == object_id)))
            )
        )
