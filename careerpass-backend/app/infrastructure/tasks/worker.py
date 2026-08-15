"""Celery worker entry point for constrained runtime and resume-parse tasks."""

import asyncio
import random
from uuid import UUID

from billiard.exceptions import SoftTimeLimitExceeded
from celery import Celery

from app.core.config import get_settings
from app.infrastructure.database import create_database
from app.infrastructure.mineru_mcp import MineruMcpAdapter
from app.infrastructure.mineru_mcp_client import MineruStdioClient
from app.infrastructure.qwen_profile import QwenProfileAdapter
from app.infrastructure.storage import LocalObjectStorage
from app.infrastructure.tasks.celery_app import create_celery_app
from app.parsers.job_description import parse_job_description
from app.parsers.resume_pdf import compose_resume_extraction_source, extract_native_pdf_text
from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.document_parsing_repository import (
    DocumentParsingRepository,
)
from app.repositories.document_parsing_repository import (
    ResumeStorageUnavailableError as RepositoryStorageUnavailableError,
)
from app.repositories.job_description_repository import (
    JobDescriptionRepository,
    JobDescriptionStorageUnavailableError,
)
from app.services.async_task_execution_service import AsyncTaskExecutionService
from app.services.job_description_worker_service import (
    JobDescriptionParseResult,
    JobDescriptionParseWorkerService,
)
from app.services.resume_parse_finalization_service import ResumeParseFinalizationService
from app.services.resume_parse_worker_service import (
    ResumeParseWorkerService,
    ResumeStorageUnavailableError,
)

settings = get_settings()
celery_app = create_celery_app(
    str(settings.redis_url),
    task_time_limit_seconds=settings.celery_task_time_limit_seconds,
    task_soft_time_limit_seconds=settings.celery_task_soft_time_limit_seconds,
    task_max_retries=settings.celery_task_max_retries,
    retry_backoff_max_seconds=settings.celery_retry_backoff_max_seconds,
)


async def run_resume_parse_task(task_run_id: UUID, retry_count: int) -> str:
    """Build one isolated Worker execution and return only its safe scheduling outcome."""
    settings.require_resume_parsing_credentials()
    mineru_timeout = min(45.0, settings.celery_task_soft_time_limit_seconds * 0.4)
    qwen_timeout = max(10.0, settings.celery_task_soft_time_limit_seconds - 5.0)
    database = create_database(str(settings.database_url), pool_size=settings.database_pool_size)
    storage = LocalObjectStorage(settings.object_storage_root)
    mineru = MineruMcpAdapter(
        tool=MineruStdioClient(
            command=settings.mineru_mcp_command,
            command_args=settings.mineru_mcp_command_args,
            api_token=settings.mineru_api_token.get_secret_value(),
            timeout_seconds=mineru_timeout,
        )
    )
    qwen = QwenProfileAdapter(
        api_key=settings.qwen_api_key.get_secret_value(),
        base_url=settings.qwen_base_url,
        model=settings.qwen_model,
        timeout_seconds=qwen_timeout,
    )

    async def claim(value: UUID):
        async with database.session_factory() as session:
            return await AsyncTaskExecutionService(
                repository=AsyncTaskRepository(session),
                lease_seconds=settings.celery_execution_lease_seconds,
            ).claim(value)

    async def release_for_retry(lease):
        async with database.session_factory() as session:
            return await AsyncTaskExecutionService(
                repository=AsyncTaskRepository(session),
                lease_seconds=settings.celery_execution_lease_seconds,
            ).release_for_retry(lease)

    async def read_resume(resume_id: UUID) -> bytes:
        async with database.session_factory() as session:
            try:
                return await DocumentParsingRepository(session).read_resume_for_processing(
                    resume_id, storage.read
                )
            except RepositoryStorageUnavailableError as exc:
                raise ResumeStorageUnavailableError from exc

    async def extract_resume_source(content: bytes) -> str:
        try:
            native_text = extract_native_pdf_text(content)
        except ValueError:
            return await mineru.extract_markdown(content)
        return compose_resume_extraction_source(native_text, "")

    async def succeed(lease, profile):
        async with database.session_factory() as session:
            return await ResumeParseFinalizationService(
                repository=DocumentParsingRepository(session)
            ).succeed(lease, profile)

    async def fail(lease, failure_code):
        async with database.session_factory() as session:
            return await ResumeParseFinalizationService(
                repository=DocumentParsingRepository(session)
            ).fail(lease, failure_code)

    try:
        outcome = await ResumeParseWorkerService(
            claim=claim,
            release_for_retry=release_for_retry,
            read_resume=read_resume,
            extract_markdown=extract_resume_source,
            extract_profile=qwen.extract_profile,
            succeed=succeed,
            fail=fail,
            max_retries=settings.celery_task_max_retries,
        ).process(task_run_id=task_run_id, retry_count=retry_count)
        return outcome.action
    finally:
        await database.close()


async def run_job_jd_parse_task(task_run_id: UUID, retry_count: int) -> str:  # pragma: no cover
    """Run one deterministic JD parse using the durable S-03 execution lease."""
    database = create_database(str(settings.database_url), pool_size=settings.database_pool_size)
    storage = LocalObjectStorage(settings.object_storage_root)

    async def claim(value: UUID):
        async with database.session_factory() as session:
            return await AsyncTaskExecutionService(
                repository=AsyncTaskRepository(session),
                lease_seconds=settings.celery_execution_lease_seconds,
            ).claim(value)

    async def release_for_retry(lease):
        async with database.session_factory() as session:
            return await AsyncTaskExecutionService(
                repository=AsyncTaskRepository(session),
                lease_seconds=settings.celery_execution_lease_seconds,
            ).release_for_retry(lease)

    async def read_job(job_id: UUID) -> bytes:
        async with database.session_factory() as session:
            try:
                return await JobDescriptionRepository(session).read_for_worker(
                    job_id=job_id,
                    storage_key_reader=storage.read,
                )
            except JobDescriptionStorageUnavailableError:
                raise

    async def succeed(lease, parsed: JobDescriptionParseResult):
        async with database.session_factory() as session:
            return await JobDescriptionRepository(session).complete_for_execution(
                lease=lease,
                fields=parsed.fields,
                raw_sections=parsed.raw_sections,
                schema_version="v1",
            )

    async def fail(lease, semantics, reason, missing):
        async with database.session_factory() as session:
            return await JobDescriptionRepository(session).fail_for_execution(
                lease=lease,
                failure_semantics=semantics,
                failure_reason=reason,
                missing_core_fields=missing,
            )

    def parse(content: bytes) -> JobDescriptionParseResult:
        fields, raw_sections = parse_job_description(content)
        return JobDescriptionParseResult(fields=fields, raw_sections=raw_sections)

    try:
        outcome = await JobDescriptionParseWorkerService(
            claim=claim,
            release_for_retry=release_for_retry,
            read_job=read_job,
            parse=parse,
            succeed=succeed,
            fail=fail,
            max_retries=settings.celery_task_max_retries,
        ).process(task_run_id=task_run_id, retry_count=retry_count)
        return outcome.action
    finally:
        await database.close()


def _register_resume_parse_task(celery: Celery) -> None:
    """Register the fixed Worker task without accepting caller-composed task parameters."""

    @celery.task(name="careerpass.resume_parse", bind=True)
    def resume_parse(task: object, *, task_run_id: str) -> None:
        try:
            parsed_task_run_id = UUID(task_run_id)
        except ValueError:
            return
        retry_count = task.request.retries
        try:
            outcome = asyncio.run(run_resume_parse_task(parsed_task_run_id, retry_count))
        except SoftTimeLimitExceeded:
            # Celery interrupts the asyncio call before the service can finalize.
            # Close the still-valid lease through the repository boundary so the
            # task cannot remain indefinitely in running/processing.
            asyncio.run(_fail_interrupted_task(parsed_task_run_id))
            return
        if outcome != "retry":
            return
        base_delay = min(2 ** (retry_count + 1), settings.celery_retry_backoff_max_seconds)
        raise task.retry(
            max_retries=settings.celery_task_max_retries,
            countdown=random.uniform(0, base_delay),
        )


_register_resume_parse_task(celery_app)


def _register_job_jd_parse_task(celery: Celery) -> None:  # pragma: no cover
    """Register the fixed S-03 task without accepting caller-composed inputs."""

    @celery.task(name="careerpass.job_jd_parse", bind=True)
    def job_jd_parse(task: object, *, task_run_id: str) -> None:
        try:
            parsed_task_run_id = UUID(task_run_id)
        except ValueError:
            return
        retry_count = task.request.retries
        try:
            outcome = asyncio.run(run_job_jd_parse_task(parsed_task_run_id, retry_count))
        except SoftTimeLimitExceeded:
            asyncio.run(_fail_interrupted_task(parsed_task_run_id))
            return
        if outcome != "retry":
            return
        base_delay = min(2 ** (retry_count + 1), settings.celery_retry_backoff_max_seconds)
        raise task.retry(
            max_retries=settings.celery_task_max_retries,
            countdown=random.uniform(0, base_delay),
        )


_register_job_jd_parse_task(celery_app)


async def _fail_interrupted_task(task_run_id: UUID) -> bool:
    """Finalize a task interrupted by Celery while its execution lease is valid."""
    database = create_database(str(settings.database_url), pool_size=settings.database_pool_size)
    try:
        async with database.session_factory() as session:
            return await AsyncTaskRepository(session).fail_execution_after_timeout(
                task_run_id=task_run_id
            )
    finally:
        await database.close()
