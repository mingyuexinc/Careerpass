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
from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.document_parsing_repository import (
    DocumentParsingRepository,
)
from app.repositories.document_parsing_repository import (
    ResumeStorageUnavailableError as RepositoryStorageUnavailableError,
)
from app.services.async_task_execution_service import AsyncTaskExecutionService
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
    database = create_database(str(settings.database_url), pool_size=settings.database_pool_size)
    storage = LocalObjectStorage(settings.object_storage_root)
    mineru = MineruMcpAdapter(
        tool=MineruStdioClient(
            command=settings.mineru_mcp_command,
            command_args=settings.mineru_mcp_command_args,
            api_token=settings.mineru_api_token.get_secret_value(),
            timeout_seconds=settings.celery_task_soft_time_limit_seconds,
        )
    )
    qwen = QwenProfileAdapter(
        api_key=settings.qwen_api_key.get_secret_value(),
        base_url=settings.qwen_base_url,
        model=settings.qwen_model,
        timeout_seconds=settings.celery_task_soft_time_limit_seconds,
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
            extract_markdown=mineru.extract_markdown,
            extract_profile=qwen.extract_profile,
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
