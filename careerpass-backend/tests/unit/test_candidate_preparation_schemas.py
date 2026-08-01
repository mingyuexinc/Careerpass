"""Focused non-database tests for public preparation contracts and storage safety."""

from pathlib import Path
from uuid import uuid4

import pytest

from app.infrastructure.storage.local import LocalObjectStorage
from app.services.candidate_preparation_service import (
    CandidatePreparationService,
    InvalidUploadError,
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
        async def create_resume(self, **_: object) -> tuple[object, bool, bool]:
            return type("Resume", (), {"id": uuid4()})(), False, False

    async def execute() -> None:
        storage = LocalObjectStorage(str(tmp_path))
        service = CandidatePreparationService(repository=ReusingRepository(), storage=storage)  # type: ignore[arg-type]
        await service.upload_resume(
            candidate_id=uuid4(),
            content=b"%PDF-1.7",
            filename="resume.pdf",
            declared_mime="application/pdf",
            name="resume.pdf",
            idempotency_key=None,
        )

    import asyncio

    asyncio.run(execute())
    assert list(tmp_path.iterdir()) == []
