"""Repository-only persistence for candidate preparation resources."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    CandidateDocument,
    Resume,
    StoredFileObject,
)
from app.infrastructure.storage.local import StoredUpload


class IdempotencyConflictError(Exception):
    """Raised when one idempotency key is reused with a different upload intent."""


class CandidatePreparationRepository:
    """Persist candidate-owned uploads and their metadata only."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        """Expose the caller-owned transaction boundary without exposing the session."""
        return self._session.begin()

    async def create_resume(
        self, *, candidate_id: UUID, name: str, upload: StoredUpload, idempotency_key: UUID | None
    ) -> tuple[Resume, bool, bool]:
        file_object, created_file_object = await self._get_or_create_file_object(
            upload, "application/pdf"
        )
        existing = await self._resume_by_key(candidate_id, idempotency_key)
        if existing is not None:
            resume, existing_file_object = existing
            if existing_file_object.content_sha256 != upload.content_sha256:
                raise IdempotencyConflictError
            return resume, True, False
        existing = await self._resume_by_content(candidate_id, file_object.content_sha256)
        if existing is not None:
            return existing, True, False
        resume = Resume(
            candidate_id=candidate_id,
            upload_idempotency_key=idempotency_key,
            file_name=name,
            stored_file_object_id=file_object.id,
            file_type="pdf",
        )
        self._session.add(resume)
        await self._session.flush()
        return resume, False, created_file_object

    async def create_document(
        self,
        *,
        candidate_id: UUID,
        name: str,
        file_type: str,
        detected_mime_type: str,
        upload: StoredUpload,
        idempotency_key: UUID | None,
    ) -> tuple[CandidateDocument, bool, bool]:
        async with self._session.begin():
            existing = await self._document_by_key(candidate_id, idempotency_key)
            if existing is not None:
                document, file_object = existing
                if (
                    document.document_name != name
                    or file_object.content_sha256 != upload.content_sha256
                ):
                    raise IdempotencyConflictError
                return document, True, False
            existing_by_content = await self._document_by_content(
                candidate_id, upload.content_sha256
            )
            if existing_by_content is not None:
                return existing_by_content, True, False
            file_object, created_file_object = await self._get_or_create_file_object(
                upload, detected_mime_type
            )
            document = CandidateDocument(
                candidate_id=candidate_id,
                upload_idempotency_key=idempotency_key,
                document_type="other",
                document_name=name,
                file_type=file_type,
                stored_file_object_id=file_object.id,
            )
            self._session.add(document)
            await self._session.flush()
        return document, False, created_file_object

    async def list_resumes(
        self, candidate_id: UUID, page: int, page_size: int
    ) -> tuple[list[Resume], int]:
        count = await self._session.scalar(
            select(func.count()).select_from(Resume).where(Resume.candidate_id == candidate_id)
        )
        statement = (
            select(Resume)
            .where(Resume.candidate_id == candidate_id)
            .order_by(Resume.created_at.desc(), Resume.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self._session.scalars(statement)).all()), int(count or 0)

    async def list_documents(
        self, candidate_id: UUID, page: int, page_size: int
    ) -> tuple[list[CandidateDocument], int]:
        where = [CandidateDocument.candidate_id == candidate_id]
        count = await self._session.scalar(
            select(func.count()).select_from(CandidateDocument).where(*where)
        )
        statement = (
            select(CandidateDocument)
            .where(*where)
            .order_by(CandidateDocument.created_at.desc(), CandidateDocument.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self._session.scalars(statement)).all()), int(count or 0)

    async def _get_or_create_file_object(
        self, upload: StoredUpload, mime_type: str
    ) -> tuple[StoredFileObject, bool]:
        existing = await self._session.scalar(
            select(StoredFileObject).where(StoredFileObject.content_sha256 == upload.content_sha256)
        )
        if existing is not None:
            return existing, False
        value = StoredFileObject(
            storage_key=upload.storage_key,
            content_sha256=upload.content_sha256,
            detected_mime_type=mime_type,
            file_size_bytes=upload.size_bytes,
            status="ready",
        )
        self._session.add(value)
        await self._session.flush()
        return value, True

    async def _resume_by_key(
        self, candidate_id: UUID, key: UUID | None
    ) -> tuple[Resume, StoredFileObject] | None:
        if key is None:
            return None
        statement = (
            select(Resume, StoredFileObject)
            .join(StoredFileObject, Resume.stored_file_object_id == StoredFileObject.id)
            .where(
                Resume.candidate_id == candidate_id,
                Resume.upload_idempotency_key == key,
            )
        )
        return (await self._session.execute(statement)).one_or_none()

    async def _resume_by_content(
        self, candidate_id: UUID, content_sha256: str
    ) -> Resume | None:
        statement = (
            select(Resume)
            .join(StoredFileObject, Resume.stored_file_object_id == StoredFileObject.id)
            .where(
                Resume.candidate_id == candidate_id,
                StoredFileObject.content_sha256 == content_sha256,
            )
            .order_by(Resume.created_at.asc(), Resume.id.asc())
            .limit(1)
        )
        return await self._session.scalar(statement)

    async def _document_by_key(
        self, candidate_id: UUID, key: UUID | None
    ) -> tuple[CandidateDocument, StoredFileObject] | None:
        if key is None:
            return None
        statement = (
            select(CandidateDocument, StoredFileObject)
            .join(
                StoredFileObject,
                CandidateDocument.stored_file_object_id == StoredFileObject.id,
            )
            .where(
                CandidateDocument.candidate_id == candidate_id,
                CandidateDocument.upload_idempotency_key == key,
            )
        )
        return (await self._session.execute(statement)).one_or_none()

    async def _document_by_content(
        self, candidate_id: UUID, content_sha256: str
    ) -> CandidateDocument | None:
        statement = (
            select(CandidateDocument)
            .join(
                StoredFileObject,
                CandidateDocument.stored_file_object_id == StoredFileObject.id,
            )
            .where(
                CandidateDocument.candidate_id == candidate_id,
                StoredFileObject.content_sha256 == content_sha256,
            )
            .order_by(CandidateDocument.created_at.asc(), CandidateDocument.id.asc())
            .limit(1)
        )
        return await self._session.scalar(statement)
