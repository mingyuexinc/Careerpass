"""Independent callable entry point for the hourly object cleanup scheduler."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from app.infrastructure.storage.local import LocalObjectStorage
from app.repositories.object_storage_repository import ObjectStorageRepository
from app.services.object_cleanup_service import ObjectCleanupService

logger = logging.getLogger("careerpass.object_cleanup")


async def run_hourly_object_cleanup(database: object, storage: LocalObjectStorage) -> int:
    """Run one cleanup cycle; deployment schedules this entry point hourly outside Celery Beat."""
    session_factory = getattr(database, "session_factory")
    async with session_factory() as session:
        return await ObjectCleanupService(
            repository=ObjectStorageRepository(session), storage=storage
        ).run_once()


async def run_cleanup_schedule(
    cleanup: Callable[[], Awaitable[int]], *, interval_seconds: int = 3600
) -> None:
    """Run independent cleanup cycles; cancellation is the normal shutdown path."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await cleanup()
        except Exception:
            logger.warning("object cleanup cycle failed")


async def stop_cleanup_schedule(task: asyncio.Task[None]) -> None:
    """Cancel a background schedule without leaking cancellation outside shutdown."""
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
