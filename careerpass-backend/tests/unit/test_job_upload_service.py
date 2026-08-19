"""Focused tests for S-02 validation, idempotency, and transaction cleanup."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.infrastructure.storage.local import LocalObjectStorage
from app.schemas.job_upload import JobUploadResult
from app.services.job_upload_service import (
    InvalidJobUploadError,
    JobUploadInput,
    JobUploadService,
    _safe_file_name,
    _validate_upload,
)


class FakeJobRepository:
    def __init__(self) -> None:
        self.active: dict[str, SimpleNamespace] = {}
        self.created: list[SimpleNamespace] = []
        self.in_transaction = False

    @asynccontextmanager
    async def transaction(self):
        self.in_transaction = True
        try:
            yield
        finally:
            self.in_transaction = False

    async def find_active_by_digest(self, *, content_sha256: str, **_: object):
        return self.active.get(content_sha256)

    async def create_job(self, *, upload: object, **_: object):
        content_sha256 = upload.content_sha256  # type: ignore[attr-defined]
        job = SimpleNamespace(id=uuid4(), file_name=_.get("file_name"))
        self.active[content_sha256] = job
        self.created.append(job)
        return job, True


class FakeTaskRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create_or_get_queued_job_task(self, **kwargs: object):
        self.calls.append(kwargs)
        return SimpleNamespace(id=uuid4()), True


def _service(tmp_path: Path) -> tuple[JobUploadService, FakeJobRepository, FakeTaskRepository]:
    repository = FakeJobRepository()
    tasks = FakeTaskRepository()
    service = JobUploadService(
        repository=repository,  # type: ignore[arg-type]
        task_repository=tasks,  # type: ignore[arg-type]
        storage=LocalObjectStorage(str(tmp_path)),
    )
    return service, repository, tasks


def test_job_upload_validation_accepts_markdown_only() -> None:
    assert _validate_upload(b"# Role", "role.md", "text/markdown").file_type == "md"


def test_job_upload_persists_only_the_original_basename() -> None:
    assert _safe_file_name(r"C:\\fake\\001-ai-engineer.md") == "001-ai-engineer.md"
    assert _safe_file_name("  002-data.md  ") == "002-data.md"


@pytest.mark.parametrize(
    ("content", "filename", "mime"),
    [
        (b"", "role.md", "text/markdown"),
        (b"%PDF-1.7", "role.pdf", "application/pdf"),
        (
            b"role",
            "role.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (b"# role", "role.txt", "text/plain"),
        (b"\xff", "role.md", "text/markdown"),
    ],
)
def test_job_upload_validation_rejects_invalid_files(
    content: bytes, filename: str, mime: str
) -> None:
    with pytest.raises(InvalidJobUploadError):
        _validate_upload(content, filename, mime)


def test_batch_upload_creates_independent_jobs_and_allows_partial_failure(tmp_path: Path) -> None:
    service, repository, tasks = _service(tmp_path)

    async def execute():
        return await service.upload_many(
            hr_profile_id=uuid4(),
            uploads=[
                JobUploadInput(b"# first", "first.md", "text/markdown"),
                JobUploadInput(b"bad", "broken.pdf", "application/pdf"),
                JobUploadInput(b"# second", "second.md", "text/markdown"),
            ],
        )

    result = asyncio.run(execute())
    assert [item.outcome for item in result.results] == ["created", "failed", "created"]
    assert len(repository.created) == 2
    assert [job.file_name for job in repository.created] == ["first.md", "second.md"]
    assert len(tasks.calls) == 2
    assert all(call["job_id"] in {job.id for job in repository.created} for call in tasks.calls)
    assert list(tmp_path.iterdir())


def test_same_hr_same_content_returns_duplicate_without_new_task(tmp_path: Path) -> None:
    service, repository, tasks = _service(tmp_path)
    hr_profile_id = uuid4()
    upload = JobUploadInput(b"# same", "same.md", "text/markdown")

    async def execute():
        first = await service.upload_many(hr_profile_id=hr_profile_id, uploads=[upload])
        second = await service.upload_many(hr_profile_id=hr_profile_id, uploads=[upload])
        return first, second

    first, second = asyncio.run(execute())
    assert first.results[0].outcome == "created"
    assert second.results[0] == JobUploadResult(
        index=0,
        outcome="duplicate",
        job_id=first.results[0].job_id,
        task_status="existing",
    )
    assert len(repository.created) == 1
    assert len(tasks.calls) == 1
    assert len(list(tmp_path.iterdir())) == 1


def test_deleted_job_is_not_reused_by_repository_contract(tmp_path: Path) -> None:
    service, repository, tasks = _service(tmp_path)
    hr_profile_id = uuid4()
    upload = JobUploadInput(b"# deleted", "deleted.md", "text/markdown")

    async def execute():
        first = await service.upload_many(hr_profile_id=hr_profile_id, uploads=[upload])
        repository.active.clear()
        second = await service.upload_many(hr_profile_id=hr_profile_id, uploads=[upload])
        return first, second

    first, second = asyncio.run(execute())
    assert first.results[0].job_id != second.results[0].job_id
    assert second.results[0].outcome == "created"
    assert len(repository.created) == 2
    assert len(tasks.calls) == 2


def test_storage_or_handoff_failure_returns_safe_failed_result_and_cleans_file(
    tmp_path: Path,
) -> None:
    class FailingTasks(FakeTaskRepository):
        async def create_or_get_queued_job_task(self, **_: object):
            raise RuntimeError("internal failure")

    repository = FakeJobRepository()
    tasks = FailingTasks()
    service = JobUploadService(
        repository=repository,  # type: ignore[arg-type]
        task_repository=tasks,  # type: ignore[arg-type]
        storage=LocalObjectStorage(str(tmp_path)),
    )

    async def execute():
        return await service.upload_many(
            hr_profile_id=uuid4(),
            uploads=[JobUploadInput(b"# failing", "failing.md", "text/markdown")],
        )

    result = asyncio.run(execute())
    assert result.results[0].outcome == "failed"
    assert result.results[0].error_code == "persistence_failed"
    assert list(tmp_path.iterdir()) == []
