"""Tests for lease-safe resume Worker orchestration."""

import asyncio
from uuid import UUID, uuid4

from app.infrastructure.mineru_mcp import MineruUnavailableError, MineruUnreadableError
from app.repositories.async_task_repository import ExecutionLease
from app.schemas.document_parsing import ResumeProfileExtractionV1
from app.services.resume_parse_worker_service import ResumeParseWorkerService


def _lease() -> ExecutionLease:
    return ExecutionLease(
        task_run_id=uuid4(),
        task_type="resume_parse",
        resource_type="resume",
        resource_id=uuid4(),
        execution_token=uuid4(),
    )


class RecordingPorts:
    def __init__(self, error: Exception | None = None) -> None:
        self.lease = _lease()
        self.error = error
        self.released: list[ExecutionLease] = []
        self.failures: list[tuple[ExecutionLease, str]] = []
        self.successes: list[tuple[ExecutionLease, ResumeProfileExtractionV1]] = []

    async def claim(self, _: UUID) -> ExecutionLease:
        return self.lease

    async def release(self, lease: ExecutionLease) -> bool:
        self.released.append(lease)
        return True

    async def read(self, _: UUID) -> bytes:
        return b"%PDF-1.7"

    async def markdown(self, _: bytes) -> str:
        if self.error is not None:
            raise self.error
        return "Target role: Backend Engineer"

    async def profile(self, _: str) -> ResumeProfileExtractionV1:
        return ResumeProfileExtractionV1(target_job_titles=["Backend Engineer"])

    async def succeed(self, lease: ExecutionLease, profile: ResumeProfileExtractionV1) -> bool:
        self.successes.append((lease, profile))
        return True

    async def fail(self, lease: ExecutionLease, failure_code: str) -> bool:
        self.failures.append((lease, failure_code))
        return True


def _service(ports: RecordingPorts) -> ResumeParseWorkerService:
    return ResumeParseWorkerService(
        claim=ports.claim,
        release_for_retry=ports.release,
        read_resume=ports.read,
        extract_markdown=ports.markdown,
        extract_profile=ports.profile,
        succeed=ports.succeed,
        fail=ports.fail,
        max_retries=2,
    )


def test_worker_success_uses_one_claimed_lease_for_finalization() -> None:
    ports = RecordingPorts()

    outcome = asyncio.run(_service(ports).process(task_run_id=ports.lease.task_run_id, retry_count=0))

    assert outcome.action == "succeeded"
    assert ports.successes == [
        (ports.lease, ResumeProfileExtractionV1(target_job_titles=["Backend Engineer"]))
    ]
    assert not ports.released and not ports.failures


def test_retryable_failure_releases_the_matching_lease_before_retry() -> None:
    ports = RecordingPorts(MineruUnavailableError())

    outcome = asyncio.run(_service(ports).process(task_run_id=ports.lease.task_run_id, retry_count=0))

    assert outcome.action == "retry"
    assert ports.released == [ports.lease]
    assert not ports.failures


def test_terminal_failure_does_not_release_or_create_a_profile() -> None:
    ports = RecordingPorts(MineruUnreadableError())

    outcome = asyncio.run(_service(ports).process(task_run_id=ports.lease.task_run_id, retry_count=0))

    assert outcome.action == "failed"
    assert ports.failures == [(ports.lease, "file_unreadable")]
    assert not ports.released and not ports.successes


def test_retry_exhaustion_persists_the_safe_failure_code() -> None:
    ports = RecordingPorts(MineruUnavailableError())

    outcome = asyncio.run(_service(ports).process(task_run_id=ports.lease.task_run_id, retry_count=2))

    assert outcome.action == "failed"
    assert ports.failures == [(ports.lease, "internal_error")]
    assert not ports.released


def test_duplicate_or_late_delivery_has_no_side_effect() -> None:
    ports = RecordingPorts()

    async def no_lease(_: UUID) -> None:
        return None

    service = ResumeParseWorkerService(
        claim=no_lease,
        release_for_retry=ports.release,
        read_resume=ports.read,
        extract_markdown=ports.markdown,
        extract_profile=ports.profile,
        succeed=ports.succeed,
        fail=ports.fail,
        max_retries=2,
    )
    outcome = asyncio.run(service.process(task_run_id=uuid4(), retry_count=0))

    assert outcome.action == "ignored"
    assert not ports.released and not ports.failures and not ports.successes


def test_runtime_composition_uses_only_repository_backed_worker_ports(monkeypatch) -> None:
    import app.infrastructure.tasks.worker as worker

    lease = _lease()

    class Settings:
        database_url = "postgresql+asyncpg://test"
        database_pool_size = 1
        object_storage_root = ".objects"
        mineru_mcp_command = "uvx"
        mineru_mcp_command_args = ("mineru-open-mcp",)
        mineru_api_token = type("Secret", (), {"get_secret_value": lambda self: "token"})()
        qwen_api_key = type("Secret", (), {"get_secret_value": lambda self: "token"})()
        qwen_base_url = "https://example.invalid"
        qwen_model = "qwen-plus"
        celery_task_soft_time_limit_seconds = 25
        celery_execution_lease_seconds = 90
        celery_task_max_retries = 2

        def require_resume_parsing_credentials(self) -> None:
            return None

    class SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_):
            return None

    class Database:
        session_factory = staticmethod(SessionContext)

        async def close(self) -> None:
            return None

    class ExecutionService:
        def __init__(self, **_):
            return None

        async def claim(self, _: UUID) -> ExecutionLease:
            return lease

        async def release_for_retry(self, _: ExecutionLease) -> bool:
            return True

    class ParsingRepository:
        def __init__(self, _):
            return None

        async def read_resume_for_processing(self, _, __) -> bytes:
            return b"%PDF-1.7"

    class Finalizer:
        def __init__(self, **_):
            return None

        async def succeed(self, _, __) -> bool:
            return True

        async def fail(self, _, __) -> bool:
            return True

    class Mineru:
        async def extract_markdown(self, _: bytes) -> str:
            return "Target role: Backend Engineer"

    class Qwen:
        async def extract_profile(self, _: str) -> ResumeProfileExtractionV1:
            return ResumeProfileExtractionV1(target_job_titles=["Backend Engineer"])

    class Orchestrator:
        def __init__(self, **ports):
            self._ports = ports

        async def process(self, **_):
            claimed = await self._ports["claim"](lease.task_run_id)
            assert claimed == lease
            assert await self._ports["read_resume"](lease.resource_id) == b"%PDF-1.7"
            assert await self._ports["succeed"](
                lease, await self._ports["extract_profile"]("markdown")
            )
            assert await self._ports["release_for_retry"](lease)
            assert await self._ports["fail"](lease, "internal_error")
            return type("Outcome", (), {"action": "succeeded"})()

    monkeypatch.setattr(worker, "settings", Settings())
    monkeypatch.setattr(worker, "create_database", lambda *_args, **_kwargs: Database())
    monkeypatch.setattr(worker, "LocalObjectStorage", lambda _: type("Storage", (), {"read": lambda *_: b""})())
    monkeypatch.setattr(worker, "MineruStdioClient", lambda **_: object())
    monkeypatch.setattr(worker, "MineruMcpAdapter", lambda **_: Mineru())
    monkeypatch.setattr(worker, "QwenProfileAdapter", lambda **_: Qwen())
    monkeypatch.setattr(worker, "AsyncTaskExecutionService", ExecutionService)
    monkeypatch.setattr(worker, "DocumentParsingRepository", ParsingRepository)
    monkeypatch.setattr(worker, "ResumeParseFinalizationService", Finalizer)
    monkeypatch.setattr(worker, "ResumeParseWorkerService", Orchestrator)

    assert asyncio.run(worker.run_resume_parse_task(lease.task_run_id, 0)) == "succeeded"
