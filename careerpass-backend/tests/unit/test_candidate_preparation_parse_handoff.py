"""Tests for the candidate-preparation upload boundary."""

import asyncio
from contextlib import AbstractAsyncContextManager
from types import SimpleNamespace
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
        self._scalar_calls = 0
        self._inserted_file_object = False

    def begin(self) -> RecordingTransaction:
        return RecordingTransaction(self)

    async def scalar(self, _: object) -> object | None:
        self._scalar_calls += 1
        if self._inserted_file_object and self._scalar_calls == 2:
            # The locked reselect right after the Core insert observes the fresh row.
            return SimpleNamespace(
                id=uuid4(),
                status="ready",
                storage_key="a" * 32,
                content_sha256="b" * 64,
                detected_mime_type="application/pdf",
                file_size_bytes=12,
            )
        return None

    async def execute(self, _: object) -> None:
        self._inserted_file_object = True
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
    resume, replayed, created_object, replaced_key = asyncio.run(
        repository.create_resume(
            candidate_id=uuid4(),
            name="resume.pdf",
            upload=StoredUpload(storage_key="a" * 32, content_sha256="b" * 64, size_bytes=12),
            idempotency_key=None,
        )
    )

    assert replayed is False
    assert created_object is True
    assert replaced_key is None
    assert resume.file_name == "resume.pdf"
    assert not hasattr(resume, "parse_status") or resume.parse_status is None
