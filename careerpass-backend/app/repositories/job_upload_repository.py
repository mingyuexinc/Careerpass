"""Repository-only persistence for HR-owned job uploads."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Job, StoredFileObject
from app.infrastructure.storage.local import StoredUpload
from app.repositories.object_storage_repository import ObjectStorageRepository


class JobUploadRepository:
    """Persist Job, stored-file metadata, and their ownership relationship."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        return self._session.begin()

    async def find_active_by_digest(
        self, *, hr_profile_id: UUID, content_sha256: str
    ) -> Job | None:
        statement = (
            select(Job)
            .join(StoredFileObject, Job.stored_file_object_id == StoredFileObject.id)
            .where(
                Job.hr_profile_id == hr_profile_id,
                Job.deleted_at.is_(None),
                StoredFileObject.content_sha256 == content_sha256,
            )
            .order_by(Job.created_at, Job.id)
            .with_for_update()
        )
        return await self._session.scalar(statement)

    async def create_job(
        self,
        *,
        hr_profile_id: UUID,
        upload: StoredUpload,
        detected_mime_type: str,
        file_name: str | None = None,
    ) -> tuple[Job, bool, str | None]:
        acquired = await ObjectStorageRepository(self._session).acquire_for_reference(
            upload=upload, mime_type=detected_mime_type
        )
        file_object = acquired.value

        job = Job(
            hr_profile_id=hr_profile_id,
            stored_file_object_id=file_object.id,
            file_name=file_name,
        )
        self._session.add(job)
        await self._session.flush()
        return job, acquired.used_new_upload, acquired.replaced_storage_key
