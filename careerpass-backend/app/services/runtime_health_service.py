"""Application service that aggregates injected runtime dependency probes."""

import asyncio
from collections.abc import Awaitable, Callable

AsyncProbe = Callable[[], Awaitable[bool]]
SyncProbe = Callable[[], bool]


class RuntimeHealthService:
    """Expose a safe readiness decision without infrastructure details."""

    def __init__(
        self,
        *,
        database_probe: AsyncProbe,
        redis_probe: AsyncProbe,
        celery_probe: SyncProbe,
    ) -> None:
        self._database_probe = database_probe
        self._redis_probe = redis_probe
        self._celery_probe = celery_probe

    async def is_ready(self) -> bool:
        """Return true only when all required dependencies are ready."""
        database_result, redis_result = await asyncio.gather(
            self._database_probe(),
            self._redis_probe(),
            return_exceptions=True,
        )
        return database_result is True and redis_result is True and self._celery_probe() is True
