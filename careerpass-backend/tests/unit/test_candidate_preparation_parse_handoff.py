"""Tests for the candidate-preparation upload boundary."""

import asyncio
from contextlib import AbstractAsyncContextManager
from uuid import uuid4

from app.infrastructure.storage.local import StoredUpload
from app.repositories.candidate_preparation_repository import CandidatePreparationRepository


class RecordingTransaction(AbstractAsyncContextManager[None]):
    def __init__(self, session: "RecordingSession") -> None:
        self._session = session

    async def __aenter__(self) -> None:
        self._session.in_transaction = True

    async def __aexit__(self, *_: object) -> None:
        self._session.in_transaction = False


class RecordingSession:
    def __init__(self) -> None:
        self.in_transaction = False
        self.values: list[object] = []

    def begin(self) -> RecordingTransaction:
        return RecordingTransaction(self)

    async def scalar(self, _: object) -> None:
        return None

    def add(self, value: object) -> None:
        self.values.append(value)

    async def flush(self) -> None:
        for value in self.values:
            if getattr(value, "id", None) is None:
                value.id = uuid4()


def test_resume_creation_only_persists_upload_metadata() -> None:
    session = RecordingSession()
    repository = CandidatePreparationRepository(session)  # type: ignore[arg-type]
    resume, replayed, created_object = asyncio.run(
        repository.create_resume(
            candidate_id=uuid4(),
            name="resume.pdf",
            upload=StoredUpload(storage_key="a" * 32, content_sha256="b" * 64, size_bytes=12),
            idempotency_key=None,
        )
    )

    assert replayed is False
    assert created_object is True
    assert resume.file_name == "resume.pdf"
    assert not hasattr(resume, "parse_status") or resume.parse_status is None
