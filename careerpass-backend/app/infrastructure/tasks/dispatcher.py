"""Independent durable-task Dispatcher; it is deliberately not Celery Beat."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from uuid import UUID

from celery import Celery

from app.core.config import Settings, get_settings
from app.infrastructure.database import Database, create_database
from app.repositories.async_task_repository import AsyncTaskRepository, DispatchLease

logger = logging.getLogger(__name__)

_TASK_NAMES = {
    "resume_parse": "careerpass.resume_parse",
    "job_jd_parse": "careerpass.job_jd_parse",
}
Publication = Callable[[str, UUID, str], None]


class TaskDispatcher:
    """Publishes durable task runs and confirms only the matching dispatch lease."""

    def __init__(
        self,
        *,
        database: Database,
        lease_seconds: int,
        batch_size: int,
        publish: Publication,
    ) -> None:
        self._database = database
        self._lease_seconds = lease_seconds
        self._batch_size = batch_size
        self._publish = publish

    async def dispatch_once(self) -> int:
        """Publish one locked batch; interruption leaves an expiring, re-publishable lease."""
        async with self._database.session_factory() as session:
            leases = await AsyncTaskRepository(session).claim_dispatch_batch(
                batch_size=self._batch_size,
                lease_seconds=self._lease_seconds,
            )
        for lease in leases:
            await self._publish_and_confirm(lease)
        return len(leases)

    async def recover_stalled_once(self) -> int:
        """Apply the documented ten-minute stale-running safety net."""
        async with self._database.session_factory() as session:
            return await AsyncTaskRepository(session).fail_stalled_tasks()

    async def _publish_and_confirm(self, lease: DispatchLease) -> None:
        try:
            task_name = _TASK_NAMES[lease.task_type]
            await asyncio.to_thread(self._publish, task_name, lease.task_run_id, lease.celery_task_id)
        except Exception:
            logger.warning(
                "async task publication failed", extra={"task_run_id": str(lease.task_run_id)}
            )
            async with self._database.session_factory() as session:
                await AsyncTaskRepository(session).release_dispatch(
                    task_run_id=lease.task_run_id,
                    dispatch_token=lease.dispatch_token,
                )
            return
        async with self._database.session_factory() as session:
            await AsyncTaskRepository(session).confirm_dispatch(
                task_run_id=lease.task_run_id,
                dispatch_token=lease.dispatch_token,
            )


def celery_publication(celery_app: Celery) -> Publication:
    """Adapt Celery without permitting callers to compose task names or payloads."""

    def publish(task_name: str, task_run_id: UUID, celery_task_id: str) -> None:
        celery_app.send_task(
            task_name,
            kwargs={"task_run_id": str(task_run_id)},
            task_id=celery_task_id,
        )

    return publish


async def run_dispatcher_loop(dispatcher: TaskDispatcher, poll_seconds: int) -> None:
    """Run the single Dispatcher process until it is cancelled by its host."""
    while True:
        await dispatcher.dispatch_once()
        await dispatcher.recover_stalled_once()
        await asyncio.sleep(poll_seconds)


async def run_configured_dispatcher(settings: Settings) -> None:
    """Build the standalone Dispatcher process and close its database pool on shutdown."""
    from app.infrastructure.tasks.celery_app import create_celery_app

    database = create_database(str(settings.database_url), pool_size=settings.database_pool_size)
    celery_app = create_celery_app(
        str(settings.redis_url),
        task_time_limit_seconds=settings.celery_task_time_limit_seconds,
        task_soft_time_limit_seconds=settings.celery_task_soft_time_limit_seconds,
        task_max_retries=settings.celery_task_max_retries,
        retry_backoff_max_seconds=settings.celery_retry_backoff_max_seconds,
    )
    dispatcher = TaskDispatcher(
        database=database,
        lease_seconds=settings.celery_dispatch_lease_seconds,
        batch_size=settings.celery_dispatcher_batch_size,
        publish=celery_publication(celery_app),
    )
    try:
        await run_dispatcher_loop(dispatcher, settings.celery_dispatcher_poll_seconds)
    finally:
        await database.close()


def main() -> None:
    """Entrypoint used by the dedicated deployment process."""
    asyncio.run(run_configured_dispatcher(get_settings()))


if __name__ == "__main__":
    main()
