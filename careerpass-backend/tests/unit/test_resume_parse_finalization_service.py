"""Tests for lease-guarded resume parsing terminal-state orchestration."""

import asyncio
from uuid import uuid4

import pytest

from app.repositories.async_task_repository import ExecutionLease
from app.repositories.document_parsing_repository import DocumentParsingRepository
from app.schemas.document_parsing import ResumeProfileExtractionV1
from app.services.resume_parse_finalization_service import ResumeParseFinalizationService


class RecordingRepository:
    def __init__(self) -> None:
        self.success_arguments: dict[str, object] | None = None
        self.failure_arguments: dict[str, object] | None = None

    async def complete_resume_for_execution(self, **kwargs: object) -> bool:
        self.success_arguments = kwargs
        return True

    async def fail_resume_for_execution(self, **kwargs: object) -> bool:
        self.failure_arguments = kwargs
        return False


def _lease(*, task_type: str = "resume_parse", resource_type: str = "resume") -> ExecutionLease:
    return ExecutionLease(
        task_run_id=uuid4(),
        task_type=task_type,
        resource_type=resource_type,
        resource_id=uuid4(),
        execution_token=uuid4(),
    )


def test_success_forwards_only_the_matching_execution_lease_and_validated_profile() -> None:
    repository = RecordingRepository()
    service = ResumeParseFinalizationService(repository=repository)  # type: ignore[arg-type]
    lease = _lease()
    profile = ResumeProfileExtractionV1(target_job_titles=["Backend Engineer"])

    assert asyncio.run(service.succeed(lease, profile)) is True
    assert repository.success_arguments == {
        "task_run_id": lease.task_run_id,
        "resume_id": lease.resource_id,
        "execution_token": lease.execution_token,
        "profile": profile,
    }


def test_failure_forwards_only_the_matching_execution_lease_and_failure_code() -> None:
    repository = RecordingRepository()
    service = ResumeParseFinalizationService(repository=repository)  # type: ignore[arg-type]
    lease = _lease()

    assert asyncio.run(service.fail(lease, "schema_validation_failed")) is False
    assert repository.failure_arguments == {
        "task_run_id": lease.task_run_id,
        "resume_id": lease.resource_id,
        "execution_token": lease.execution_token,
        "failure_code": "schema_validation_failed",
    }


def test_non_resume_lease_is_rejected_before_any_repository_write() -> None:
    repository = RecordingRepository()
    service = ResumeParseFinalizationService(repository=repository)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        asyncio.run(service.succeed(_lease(task_type="other"), ResumeProfileExtractionV1(target_job_titles=["X"])))

    assert repository.success_arguments is None


def test_repository_terminal_guard_queries_only_the_current_running_resume_lease() -> None:
    expected = object()

    class RecordingSession:
        def __init__(self) -> None:
            self.statement: object | None = None

        async def scalar(self, statement: object) -> object:
            self.statement = statement
            return expected

    session = RecordingSession()
    result = asyncio.run(
        DocumentParsingRepository(session)._locked_running_resume_task(  # type: ignore[arg-type]
            uuid4(), uuid4(), uuid4()
        )
    )

    assert result is expected
    assert session.statement is not None
