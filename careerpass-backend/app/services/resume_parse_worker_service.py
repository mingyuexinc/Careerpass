"""Lease-safe orchestration of one resume parsing execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from app.infrastructure.mineru_mcp import MineruMcpError
from app.infrastructure.qwen_profile import QwenProfileError
from app.repositories.async_task_repository import ExecutionLease
from app.schemas.document_parsing import ParseFailureCode, ResumeProfileExtractionV1


@dataclass(frozen=True)
class ResumeParseOutcome:
    """A safe Worker instruction; it contains neither source content nor provider diagnostics."""

    action: str


class ResumeStorageUnavailableError(Exception):
    """Controlled failure returned when the leased resume cannot be read."""

    failure_code: ParseFailureCode = "storage_unavailable"
    retryable = True


class ResumeParseWorkerService:
    """Coordinate only validated ports; persistence remains behind Repository-backed callbacks."""

    def __init__(
        self,
        *,
        claim: Callable[[UUID], Awaitable[ExecutionLease | None]],
        release_for_retry: Callable[[ExecutionLease], Awaitable[bool]],
        read_resume: Callable[[UUID], Awaitable[bytes]],
        extract_markdown: Callable[[bytes], Awaitable[str]],
        extract_profile: Callable[[str], Awaitable[ResumeProfileExtractionV1]],
        succeed: Callable[[ExecutionLease, ResumeProfileExtractionV1], Awaitable[bool]],
        fail: Callable[[ExecutionLease, ParseFailureCode], Awaitable[bool]],
        max_retries: int,
    ) -> None:
        self._claim = claim
        self._release_for_retry = release_for_retry
        self._read_resume = read_resume
        self._extract_markdown = extract_markdown
        self._extract_profile = extract_profile
        self._succeed = succeed
        self._fail = fail
        self._max_retries = max_retries

    async def process(self, *, task_run_id: UUID, retry_count: int) -> ResumeParseOutcome:
        """Execute one leased parse attempt without exposing raw input or provider output."""
        lease = await self._claim(task_run_id)
        if lease is None:
            return ResumeParseOutcome(action="ignored")
        try:
            content = await self._read_resume(lease.resource_id)
            markdown = await self._extract_markdown(content)
            profile = await self._extract_profile(markdown)
        except ResumeStorageUnavailableError as error:
            return await self._resolve_failure(lease, error.failure_code, error.retryable, retry_count)
        except MineruMcpError as error:
            return await self._resolve_failure(lease, error.failure_code, error.retryable, retry_count)
        except QwenProfileError as error:
            return await self._resolve_failure(lease, error.failure_code, error.retryable, retry_count)
        except Exception:
            return await self._resolve_failure(lease, "internal_error", True, retry_count)
        return ResumeParseOutcome(action="succeeded" if await self._succeed(lease, profile) else "ignored")

    async def _resolve_failure(
        self,
        lease: ExecutionLease,
        failure_code: ParseFailureCode,
        retryable: bool,
        retry_count: int,
    ) -> ResumeParseOutcome:
        if retryable and retry_count < self._max_retries:
            return ResumeParseOutcome(
                action="retry" if await self._release_for_retry(lease) else "ignored"
            )
        return ResumeParseOutcome(
            action="failed" if await self._fail(lease, failure_code) else "ignored"
        )
