"""Unit coverage for the internal S-03 submission and status service."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.infrastructure.storage.controlled import ControlledJobDescriptionStorage
from app.repositories.job_description_repository import JobDescriptionTaskPreconditionError
from app.services.job_description_service import (
    JobDescriptionInputUnavailableError,
    JobDescriptionService,
)


class FakeJobDescriptionRepository:
    def __init__(self, job=None, task=None, view=None) -> None:
        self.job = job
        self.task = task
        self.view = view

    def transaction(self):
        @asynccontextmanager
        async def context():
            yield

        return context()

    async def find_job_by_content_digest(self, **_):
        return self.job

    async def create_or_get_queued_task(self, **_):
        return self.task, True

    async def get_task_for_hr(self, **_):
        return self.view


class PreconditionRepository(FakeJobDescriptionRepository):
    async def create_or_get_queued_task(self, **_):
        raise JobDescriptionTaskPreconditionError


def _service(tmp_path: Path, repository: FakeJobDescriptionRepository) -> JobDescriptionService:
    root = tmp_path / "jd"
    root.mkdir()
    return JobDescriptionService(
        repository=repository,  # type: ignore[arg-type]
        storage=ControlledJobDescriptionStorage(str(root)),
    )


def test_submit_uses_content_digest_and_returns_task_state(tmp_path: Path) -> None:
    root = tmp_path / "jd"
    root.mkdir()
    path = root / "role.md"
    path.write_text("# Role", encoding="utf-8")
    job = SimpleNamespace(id=uuid4())
    task = SimpleNamespace(id=uuid4(), status="queued")
    repository = FakeJobDescriptionRepository(job=job, task=task)
    service = JobDescriptionService(
        repository=repository,  # type: ignore[arg-type]
        storage=ControlledJobDescriptionStorage(str(root)),
    )

    result = asyncio.run(service.submit(hr_profile_id=uuid4(), local_path=str(path)))

    assert result.task_id == task.id
    assert result.status == "queued"


def test_submit_rejects_path_outside_controlled_root(tmp_path: Path) -> None:
    service = _service(
        tmp_path,
        FakeJobDescriptionRepository(job=SimpleNamespace(id=uuid4())),
    )
    outside = tmp_path / "outside.md"
    outside.write_text("# Role", encoding="utf-8")

    with pytest.raises(JobDescriptionInputUnavailableError):
        asyncio.run(service.submit(hr_profile_id=uuid4(), local_path=str(outside)))


def test_submit_rejects_unregistered_content(tmp_path: Path) -> None:
    root = tmp_path / "jd"
    root.mkdir()
    path = root / "role.md"
    path.write_text("# Role", encoding="utf-8")
    service = JobDescriptionService(
        repository=FakeJobDescriptionRepository(job=None),  # type: ignore[arg-type]
        storage=ControlledJobDescriptionStorage(str(root)),
    )

    with pytest.raises(JobDescriptionInputUnavailableError):
        asyncio.run(service.submit(hr_profile_id=uuid4(), local_path=str(path)))


def test_submit_hides_task_precondition_failure(tmp_path: Path) -> None:
    root = tmp_path / "jd"
    root.mkdir()
    path = root / "role.md"
    path.write_text("# Role", encoding="utf-8")
    service = JobDescriptionService(
        repository=PreconditionRepository(job=SimpleNamespace(id=uuid4())),  # type: ignore[arg-type]
        storage=ControlledJobDescriptionStorage(str(root)),
    )

    with pytest.raises(JobDescriptionInputUnavailableError):
        asyncio.run(service.submit(hr_profile_id=uuid4(), local_path=str(path)))


def test_get_result_hides_snapshot_on_failure_and_returns_not_found_as_none(tmp_path: Path) -> None:
    task = SimpleNamespace(
        id=uuid4(),
        status="failed",
        failure_semantics="core_fields_missing",
        failure_reason="missing_core_fields",
        missing_core_fields=["requirements"],
    )
    view = SimpleNamespace(
        task=task,
        job_id=uuid4(),
        snapshot=SimpleNamespace(
            id=uuid4(),
            schema_version="v1",
            fields={"title": "must not be returned"},
        ),
    )
    repository = FakeJobDescriptionRepository(view=view)
    service = _service(tmp_path, repository)

    result = asyncio.run(service.get_result(hr_profile_id=uuid4(), task_id=task.id))
    assert result is not None
    assert result.matching_status is None
    assert result.snapshot_id is None
    assert result.fields is None
    assert result.missing_core_fields == ["requirements"]

    repository.view = None
    assert asyncio.run(service.get_result(hr_profile_id=uuid4(), task_id=uuid4())) is None
