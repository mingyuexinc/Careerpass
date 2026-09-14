"""Repository operations for the internal object-directory lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    CandidateDocument,
    Job,
    MessageAttachment,
    Resume,
    StoredFileObject,
)
from app.infrastructure.storage.local import StoredUpload


@dataclass(frozen=True)
class CleanupClaim:
    """An unreferenced object exclusively claimed for physical deletion."""

    object_id: UUID
    storage_key: str
    previous_status: str


@dataclass(frozen=True)
class AcquiredFileObject:
    """A ready object safe for a new reference, plus its upload bookkeeping."""

    value: StoredFileObject
    used_new_upload: bool
    replaced_storage_key: str | None


class ObjectStorageRepository:
    """Own transactional state transitions for stored-file cleanup."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def acquire_for_reference(
        self, *, upload: StoredUpload, mime_type: str
    ) -> AcquiredFileObject:
        """Return the ready object for this content, reviving a dying row when held.

        Must run inside the caller's transaction so the object and its new
        reference commit or roll back together. A non-ready object holding the
        content hash is unreferenced by lifecycle definition, so pointing it at
        the fresh upload is safe and keeps the hash unique constraint intact.
        """
        existing = await self._locked_object_by_hash(upload.content_sha256)
        if existing is not None:
            return self._as_ready_reference(existing, upload, mime_type)
        statement = (
            postgres_insert(StoredFileObject)
            .values(
                storage_key=upload.storage_key,
                content_sha256=upload.content_sha256,
                detected_mime_type=mime_type,
                file_size_bytes=upload.size_bytes,
                status="ready",
            )
            .on_conflict_do_nothing(index_elements=[StoredFileObject.content_sha256])
        )
        await self._session.execute(statement)
        winner = await self._locked_object_by_hash(upload.content_sha256)
        if winner is None:
            raise RuntimeError("stored file object acquisition failed")
        return self._as_ready_reference(winner, upload, mime_type)

    async def _locked_object_by_hash(self, content_sha256: str) -> StoredFileObject | None:
        return await self._session.scalar(
            select(StoredFileObject)
            .where(StoredFileObject.content_sha256 == content_sha256)
            .with_for_update()
        )

    def _as_ready_reference(
        self, value: StoredFileObject, upload: StoredUpload, mime_type: str
    ) -> AcquiredFileObject:
        if value.status == "ready":
            return AcquiredFileObject(
                value,
                used_new_upload=value.storage_key == upload.storage_key,
                replaced_storage_key=None,
            )
        replaced_storage_key = value.storage_key
        value.status = "ready"
        value.storage_key = upload.storage_key
        value.detected_mime_type = mime_type
        value.file_size_bytes = upload.size_bytes
        return AcquiredFileObject(
            value,
            used_new_upload=True,
            replaced_storage_key=replaced_storage_key,
        )

    async def claim_expired_unreferenced(
        self, *, older_than: datetime, limit: int
    ) -> list[CleanupClaim]:
        async with self._session.begin():
            has_resume = exists(
                select(1).where(
                    Resume.stored_file_object_id == StoredFileObject.id,
                    Resume.deleted_at.is_(None),
                )
            )
            has_document = exists(
                select(1).where(
                    CandidateDocument.stored_file_object_id == StoredFileObject.id,
                    CandidateDocument.deleted_at.is_(None),
                )
            )
            has_active_job = exists(
                select(1).where(
                    Job.stored_file_object_id == StoredFileObject.id,
                    Job.deleted_at.is_(None),
                )
            )
            has_active_attachment = exists(
                select(1).where(
                    MessageAttachment.stored_file_object_id == StoredFileObject.id,
                    MessageAttachment.expires_at > datetime.now(UTC),
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
                    ~has_active_attachment,
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
            select(
                exists(
                    select(1).where(
                        Resume.stored_file_object_id == object_id,
                        Resume.deleted_at.is_(None),
                    )
                )
            )
        )
        if resume_exists:
            return True
        document_exists = await self._session.scalar(
            select(
                exists(
                    select(1).where(
                        CandidateDocument.stored_file_object_id == object_id,
                        CandidateDocument.deleted_at.is_(None),
                    )
                )
            )
        )
        if document_exists:
            return True
        return bool(await self._session.scalar(select(exists(select(1).where(
            MessageAttachment.stored_file_object_id == object_id,
            MessageAttachment.expires_at > datetime.now(UTC),
        )))))
