"""Unit coverage for lease-safe S-03 worker decisions."""

import asyncio
from uuid import uuid4

from app.repositories.async_task_repository import ExecutionLease
from app.repositories.job_description_repository import (
    JobDescriptionContentInvalidError,
    JobDescriptionStorageUnavailableError,
)
from app.schemas.job_description import ParsedJobDescriptionFields
from app.services.job_description_worker_service import (
    JobDescriptionParseResult,
    JobDescriptionParseWorkerService,
)


def _lease() -> ExecutionLease:
    return ExecutionLease(
        task_run_id=uuid4(),
        task_type="job_jd_parse",
        resource_type="job",
        resource_id=uuid4(),
        execution_token=uuid4(),
    )


def _result() -> JobDescriptionParseResult:
    value = ParsedJobDescriptionFields.model_validate(
        {
            "title": {"raw": "工程师", "source_heading": "岗位名称", "source_order": 0},
            "location": {"raw": "上海", "source_heading": "工作地点", "source_order": 1},
            "salary_range": {
                "raw": "20k/月",
                "min": 20_000,
                "max": 20_000,
                "source_heading": "薪资",
                "source_order": 2,
            },
            "responsibilities": {
                "raw": "负责开发",
                "items": [],
                "source_heading": "岗位职责",
                "source_order": 3,
            },
            "requirements": {
                "raw": "熟悉 Python",
                "items": [],
                "source_heading": "任职要求",
                "source_order": 4,
            },
        }
    )
    return JobDescriptionParseResult(fields=value, raw_sections=[])


def test_core_field_failure_is_terminal_and_not_retried() -> None:
    lease = _lease()
    failures: list[tuple[object, ...]] = []

    async def claim(_):
        return lease

    async def release(_):
        raise AssertionError("core field failures must not retry")

    async def read(_):
        return b"content"

    def parse(_):
        from app.parsers.job_description import JobDescriptionParseError

        raise JobDescriptionParseError(["requirements"])

    async def succeed(*_):
        raise AssertionError

    async def fail(*args):
        failures.append(args)
        return True

    outcome = asyncio.run(
        JobDescriptionParseWorkerService(
            claim=claim,
            release_for_retry=release,
            read_job=read,
            parse=parse,
            succeed=succeed,
            fail=fail,
            max_retries=2,
        ).process(task_run_id=lease.task_run_id, retry_count=0)
    )

    assert outcome.action == "failed"
    assert failures[0][1:] == ("core_fields_missing", "missing_core_fields", ["requirements"])


def test_temporary_failure_retries_then_becomes_retry_exhausted() -> None:
    lease = _lease()
    releases = 0
    failures: list[tuple[object, ...]] = []

    async def claim(_):
        return lease

    async def release(_):
        nonlocal releases
        releases += 1
        return True

    async def read(_):
        return b"content"

    def parse(_):
        raise RuntimeError("temporary")

    async def succeed(*_):
        raise AssertionError

    async def fail(*args):
        failures.append(args)
        return True

    worker = JobDescriptionParseWorkerService(
        claim=claim,
        release_for_retry=release,
        read_job=read,
        parse=parse,
        succeed=succeed,
        fail=fail,
        max_retries=2,
    )
    first = asyncio.run(worker.process(task_run_id=lease.task_run_id, retry_count=0))
    final = asyncio.run(worker.process(task_run_id=lease.task_run_id, retry_count=2))

    assert first.action == "retry"
    assert final.action == "failed"
    assert releases == 1
    assert failures[0][1:3] == ("temporary_technical_failure", "retry_exhausted")


def test_storage_unavailable_is_retried_then_exposed_as_manual_failure() -> None:
    lease = _lease()
    releases = 0
    failures: list[tuple[object, ...]] = []

    async def claim(_):
        return lease

    async def release(_):
        nonlocal releases
        releases += 1
        return True

    async def read(_):
        raise JobDescriptionStorageUnavailableError

    async def succeed(*_):
        raise AssertionError

    async def fail(*args):
        failures.append(args)
        return True

    worker = JobDescriptionParseWorkerService(
        claim=claim,
        release_for_retry=release,
        read_job=read,
        parse=lambda _: _result(),
        succeed=succeed,
        fail=fail,
        max_retries=2,
    )
    first = asyncio.run(worker.process(task_run_id=lease.task_run_id, retry_count=0))
    final = asyncio.run(worker.process(task_run_id=lease.task_run_id, retry_count=2))

    assert first.action == "retry"
    assert final.action == "failed"
    assert releases == 1
    assert failures[0][1:] == ("input_unavailable", "retry_exhausted", None)


def test_invalid_content_is_manual_failure_without_retry() -> None:
    lease = _lease()
    failures: list[tuple[object, ...]] = []

    async def claim(_):
        return lease

    async def release(_):
        raise AssertionError("invalid content must not retry")

    async def read(_):
        raise JobDescriptionContentInvalidError

    async def succeed(*_):
        raise AssertionError

    async def fail(*args):
        failures.append(args)
        return True

    outcome = asyncio.run(
        JobDescriptionParseWorkerService(
            claim=claim,
            release_for_retry=release,
            read_job=read,
            parse=lambda _: _result(),
            succeed=succeed,
            fail=fail,
            max_retries=2,
        ).process(task_run_id=lease.task_run_id, retry_count=0)
    )

    assert outcome.action == "failed"
    assert failures[0][1:] == ("input_invalid", "invalid_content", None)


def test_success_returns_validated_parse_result() -> None:
    lease = _lease()
    successes: list[JobDescriptionParseResult] = []

    async def claim(_):
        return lease

    async def release(_):
        return True

    async def read(_):
        return b"content"

    async def succeed(_, parsed):
        successes.append(parsed)
        return True

    async def fail(*_):
        raise AssertionError

    outcome = asyncio.run(
        JobDescriptionParseWorkerService(
            claim=claim,
            release_for_retry=release,
            read_job=read,
            parse=lambda _: _result(),
            succeed=succeed,
            fail=fail,
            max_retries=2,
        ).process(task_run_id=lease.task_run_id, retry_count=0)
    )

    assert outcome.action == "succeeded"
    assert successes[0].fields.title.raw == "工程师"
