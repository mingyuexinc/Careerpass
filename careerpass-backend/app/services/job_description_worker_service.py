"""Lease-safe orchestration for one deterministic S-03 execution attempt."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from app.parsers.job_description import JobDescriptionParseError
from app.repositories.async_task_repository import ExecutionLease
from app.repositories.job_description_repository import JobDescriptionStorageUnavailableError
from app.schemas.job_description import ParsedJobDescriptionFields


@dataclass(frozen=True)
class JobDescriptionParseResult:
    fields: ParsedJobDescriptionFields
    raw_sections: list[dict[str, object]]


@dataclass(frozen=True)
class JobDescriptionParseOutcome:
    action: str


class JobDescriptionParseWorkerService:
    """Coordinate validated ports while keeping persistence behind Repository callbacks."""

    def __init__(
        self,
        *,
        claim: Callable[[UUID], Awaitable[ExecutionLease | None]],
        release_for_retry: Callable[[ExecutionLease], Awaitable[bool]],
        read_job: Callable[[UUID], Awaitable[bytes]],
        parse: Callable[[bytes], JobDescriptionParseResult],
        succeed: Callable[[ExecutionLease, JobDescriptionParseResult], Awaitable[bool]],
        fail: Callable[[ExecutionLease, str, str, list[str] | None], Awaitable[bool]],
        max_retries: int,
    ) -> None:
        self._claim = claim
        self._release_for_retry = release_for_retry
        self._read_job = read_job
        self._parse = parse
        self._succeed = succeed
        self._fail = fail
        self._max_retries = max_retries

    async def process(self, *, task_run_id: UUID, retry_count: int) -> JobDescriptionParseOutcome:
        lease = await self._claim(task_run_id)
        if lease is None:
            return JobDescriptionParseOutcome(action="ignored")
        try:
            content = await self._read_job(lease.resource_id)
        except JobDescriptionStorageUnavailableError:
            return await self._resolve_failure(
                lease, "input_unavailable", "file_unavailable", None, False, retry_count
            )
        try:
            parsed = self._parse(content)
        except JobDescriptionParseError as error:
            if error.missing_core_fields == ["input_unavailable"]:
                return await self._resolve_failure(
                    lease, "input_unavailable", "file_unavailable", None, False, retry_count
                )
            return await self._resolve_failure(
                lease,
                "core_fields_missing",
                "missing_core_fields",
                error.missing_core_fields,
                False,
                retry_count,
            )
        except Exception:
            return await self._resolve_failure(
                lease,
                "temporary_technical_failure",
                "retry_exhausted" if retry_count >= self._max_retries else "temporary_failure",
                None,
                True,
                retry_count,
            )
        return JobDescriptionParseOutcome(
            action="succeeded" if await self._succeed(lease, parsed) else "ignored"
        )

    async def _resolve_failure(
        self,
        lease: ExecutionLease,
        failure_semantics: str,
        failure_reason: str,
        missing_core_fields: list[str] | None,
        retryable: bool,
        retry_count: int,
    ) -> JobDescriptionParseOutcome:
        if retryable and retry_count < self._max_retries:
            return JobDescriptionParseOutcome(
                action="retry" if await self._release_for_retry(lease) else "ignored"
            )
        return JobDescriptionParseOutcome(
            action=(
                "failed"
                if await self._fail(
                    lease, failure_semantics, failure_reason, missing_core_fields
                )
                else "ignored"
            )
        )
