"""Focused non-database tests for public preparation contracts and storage safety."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.infrastructure.storage.local import LocalObjectStorage
from app.services.candidate_preparation_service import (
    CandidatePreparationService,
    InvalidUploadError,
    _display_name,
    _validate_document_upload,
    _validate_upload,
)


def test_local_storage_uses_opaque_keys_and_round_trips_content(tmp_path: Path) -> None:
    storage = LocalObjectStorage(str(tmp_path))
    stored = storage.put(b"%PDF-1.4 test")

    assert len(stored.storage_key) == 32
    assert storage.read(stored.storage_key) == b"%PDF-1.4 test"
    assert str(tmp_path) not in stored.storage_key


def test_local_storage_rejects_non_opaque_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        LocalObjectStorage(str(tmp_path)).read("../sensitive")


@pytest.mark.parametrize(
    ("filename", "mime", "content"),
    [
        ("resume.pdf", "application/pdf", b"not-a-pdf"),
        ("resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"x"),
        ("resume.pdf", "text/plain", b"%PDF-1.4"),
    ],
)
def test_resume_upload_validation_rejects_inconsistent_type(
    filename: str, mime: str, content: bytes
) -> None:
    with pytest.raises(InvalidUploadError):
        _validate_upload(content, filename, mime, {"pdf": "application/pdf"})


def test_resume_upload_validation_accepts_pdf() -> None:
    value = _validate_upload(b"%PDF-1.7", "resume.pdf", "application/pdf", {"pdf": "application/pdf"})

    assert value.file_type == "pdf"
    assert value.mime_type == "application/pdf"


def test_resume_upload_removes_transient_file_when_content_object_is_reused(
    tmp_path: Path,
) -> None:
    class ReusingRepository:
        async def has_other_resume(self, **_: object) -> bool:
            return False

        async def create_resume(self, **_: object) -> tuple[object, bool, bool]:
            return type("Resume", (), {"id": uuid4()})(), False, False

        @asynccontextmanager
        async def transaction(self):
            yield

    class ReusingTaskRepository:
        async def create_or_get_queued_resume_task(self, **_: object) -> tuple[object, bool]:
            return object(), False

    async def execute() -> None:
        storage = LocalObjectStorage(str(tmp_path))
        service = CandidatePreparationService(
            repository=ReusingRepository(),
            task_repository=ReusingTaskRepository(),
            storage=storage,
        )  # type: ignore[arg-type]
        await service.upload_resume(
            candidate_id=uuid4(),
            content=b"%PDF-1.7",
            filename="resume.pdf",
            declared_mime="application/pdf",
            name="resume.pdf",
            idempotency_key=None,
        )

    asyncio.run(execute())
    assert list(tmp_path.iterdir()) == []


def test_resume_upload_returns_processing_and_creates_queued_task(tmp_path: Path) -> None:
    class RecordingRepository:
        async def has_other_resume(self, **_: object) -> bool:
            return False

        @asynccontextmanager
        async def transaction(self):
            yield

        async def create_resume(self, **_: object) -> tuple[object, bool, bool]:
            return type("Resume", (), {"id": uuid4()})(), False, True

    class RecordingTaskRepository:
        received: dict[str, object] | None = None

        async def create_or_get_queued_resume_task(self, **kwargs: object) -> tuple[object, bool]:
            self.received = kwargs
            return object(), True

    async def execute() -> tuple[object, dict[str, object]]:
        task_repository = RecordingTaskRepository()
        service = CandidatePreparationService(
            repository=RecordingRepository(),
            task_repository=task_repository,
            storage=LocalObjectStorage(str(tmp_path)),
        )  # type: ignore[arg-type]
        result = await service.upload_resume(
            candidate_id=candidate_id,
            content=b"%PDF-1.7",
            filename="resume.pdf",
            declared_mime="application/pdf",
            name="resume.pdf",
            idempotency_key=None,
        )
        return result, task_repository.received or {}

    candidate_id = uuid4()
    result, received = asyncio.run(execute())

    assert result.parse_status == "processing"
    assert received["candidate_id"] == candidate_id
    assert received["resume_id"] == result.resume_id


def test_resume_upload_reuses_same_content_without_creating_a_second_task(tmp_path: Path) -> None:
    resume_id = uuid4()

    class ReusingRepository:
        async def has_other_resume(self, **_: object) -> bool:
            return False

        @asynccontextmanager
        async def transaction(self):
            yield

        async def create_resume(self, **_: object) -> tuple[object, bool, bool]:
            return SimpleNamespace(id=resume_id, parse_status="succeeded"), True, False

    class FailingTaskRepository:
        async def create_or_get_queued_resume_task(self, **_: object) -> tuple[object, bool]:
            raise AssertionError("same-content resume must not create another parse task")

    async def execute() -> object:
        service = CandidatePreparationService(
            repository=ReusingRepository(),
            task_repository=FailingTaskRepository(),
            storage=LocalObjectStorage(str(tmp_path)),
        )  # type: ignore[arg-type]
        return await service.upload_resume(
            candidate_id=uuid4(),
            content=b"%PDF-1.7",
            filename="same-resume.pdf",
            declared_mime="application/pdf",
            name=None,
            idempotency_key=None,
        )

    result = asyncio.run(execute())

    assert result.resume_id == resume_id
    assert result.parse_status == "succeeded"
    assert list(tmp_path.iterdir()) == []


def test_resume_upload_cleans_transient_file_when_task_creation_fails(tmp_path: Path) -> None:
    class FailingRepository:
        async def has_other_resume(self, **_: object) -> bool:
            return False

        @asynccontextmanager
        async def transaction(self):
            yield

        async def create_resume(self, **_: object) -> tuple[object, bool, bool]:
            return SimpleNamespace(id=uuid4()), False, True

    class FailingTaskRepository:
        async def create_or_get_queued_resume_task(self, **_: object) -> tuple[object, bool]:
            raise RuntimeError("task creation failed")

    async def execute() -> None:
        service = CandidatePreparationService(
            repository=FailingRepository(),
            task_repository=FailingTaskRepository(),
            storage=LocalObjectStorage(str(tmp_path)),
        )  # type: ignore[arg-type]
        with pytest.raises(RuntimeError, match="task creation failed"):
            await service.upload_resume(
                candidate_id=uuid4(),
                content=b"%PDF-1.7",
                filename="resume.pdf",
                declared_mime="application/pdf",
                name=None,
                idempotency_key=None,
            )

    asyncio.run(execute())
    assert list(tmp_path.iterdir()) == []


def test_document_upload_reuses_object_and_returns_created_result(tmp_path: Path) -> None:
    class Repository:
        async def create_document(self, **_: object) -> tuple[object, bool, bool]:
            return SimpleNamespace(
                id=uuid4(), file_type="md", created_at=datetime.now(UTC)
            ), False, False

    async def execute() -> object:
        service = CandidatePreparationService(
            repository=Repository(),
            task_repository=object(),
            storage=LocalObjectStorage(str(tmp_path)),
        )  # type: ignore[arg-type]
        result = await service.upload_documents(
            candidate_id=uuid4(),
            uploads=[(b"# notes", "notes.md", "text/markdown")],
            idempotency_key=None,
        )
        return result.results[0]

    result = asyncio.run(execute())
    assert result.candidate_document_id is not None
    assert result.result == "created"
    assert result.upload_status == "success"
    assert list(tmp_path.iterdir()) == []


def test_document_upload_cleans_transient_file_when_repository_fails(tmp_path: Path) -> None:
    class FailingRepository:
        async def create_document(self, **_: object) -> tuple[object, bool, bool]:
            raise RuntimeError("document creation failed")

    async def execute() -> None:
        service = CandidatePreparationService(
            repository=FailingRepository(),
            task_repository=object(),
            storage=LocalObjectStorage(str(tmp_path)),
        )  # type: ignore[arg-type]
        result = await service.upload_documents(
            candidate_id=uuid4(),
            uploads=[(b"# notes", "notes.md", "text/markdown")],
            idempotency_key=None,
        )
        assert result.results[0].result == "failed"
        assert result.results[0].failure_code == "internal_error"

    asyncio.run(execute())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("filename", "mime", "content", "file_type"),
    [
        ("portfolio.pdf", "application/pdf", b"%PDF-1.7", "pdf"),
        ("portfolio.md", "text/markdown", b"# Portfolio", "md"),
        ("portfolio.jpg", "image/jpeg", b"\xff\xd8\xff\xe0", "jpg"),
        ("portfolio.png", "image/png", b"\x89PNG\r\n\x1a\n", "png"),
    ],
)
def test_document_upload_validation_accepts_supported_formats(
    filename: str, mime: str, content: bytes, file_type: str
) -> None:
    value = _validate_document_upload(content, filename, mime)

    assert value.file_type == file_type


def test_document_upload_returns_storage_failure_without_persisting_a_record() -> None:
    class FailingStorage:
        def put(self, _: bytes) -> object:
            raise OSError("storage unavailable")

    class Repository:
        async def create_document(self, **_: object) -> tuple[object, bool, bool]:
            raise AssertionError("storage failure must happen before repository access")

    async def execute() -> object:
        service = CandidatePreparationService(
            repository=Repository(),
            task_repository=object(),
            storage=FailingStorage(),  # type: ignore[arg-type]
        )  # type: ignore[arg-type]
        result = await service.upload_documents(
            candidate_id=uuid4(),
            uploads=[(b"# notes", "notes.md", "text/markdown")],
            idempotency_key=None,
        )
        return result.results[0]

    result = asyncio.run(execute())

    assert result.result == "failed"
    assert result.failure_code == "storage_unavailable"


def test_list_methods_map_repository_rows_to_safe_responses() -> None:
    created_at = datetime.now(UTC)
    resume = SimpleNamespace(
        id=uuid4(),
        file_name="resume.pdf",
        parse_status="processing",
        failure_code=None,
        created_at=created_at,
    )
    document = SimpleNamespace(
        id=uuid4(), document_name="notes.md", file_type="md", created_at=created_at
    )

    class Repository:
        async def list_resumes(self, *_: object) -> tuple[list[object], int]:
            return [resume], 1

        async def list_documents(self, *_: object) -> tuple[list[object], int]:
            return [document], 1

    async def execute() -> tuple[object, object]:
        service = CandidatePreparationService(
            repository=Repository(),
            task_repository=object(),
            storage=object(),
        )  # type: ignore[arg-type]
        return (
            await service.list_resumes(uuid4(), 1, 20),
            await service.list_documents(uuid4(), 1, 20),
        )

    resumes, documents = asyncio.run(execute())
    assert resumes.total == 1
    assert resumes.list[0].name == "resume.pdf"
    assert resumes.list[0].parse_status == "processing"
    assert documents.total == 1
    assert documents.list[0].name == "notes.md"
    assert documents.list[0].file_type == "md"
    assert documents.list[0].upload_status == "success"


@pytest.mark.parametrize(
    ("filename", "mime", "content"),
    [
        ("photo.jpg", "image/jpeg", b"not-jpeg"),
        ("notes.md", "text/markdown", b"\xff"),
        ("resume.pdf", "application/pdf", b""),
    ],
)
def test_upload_validation_rejects_invalid_content_boundaries(
    filename: str, mime: str, content: bytes
) -> None:
    with pytest.raises(InvalidUploadError):
        _validate_upload(
            content,
            filename,
            mime,
            {
                "pdf": "application/pdf",
                "md": "text/markdown",
                "jpg": "image/jpeg",
            },
        )


def test_display_name_rejects_empty_or_oversized_values() -> None:
    with pytest.raises(InvalidUploadError):
        _display_name("   ", "resume.pdf", "resume", "pdf")
    with pytest.raises(InvalidUploadError):
        _display_name("x" * 256, "resume.pdf", "resume", "pdf")
