"""Tests for dependency-agnostic runtime readiness aggregation."""

import asyncio

from app.services.runtime_health_service import RuntimeHealthService


async def _true_probe() -> bool:
    return True


async def _false_probe() -> bool:
    return False


def test_runtime_health_service_requires_every_probe() -> None:
    ready_service = RuntimeHealthService(
        database_probe=_true_probe,
        redis_probe=_true_probe,
        celery_probe=lambda: True,
    )
    unavailable_service = RuntimeHealthService(
        database_probe=_false_probe,
        redis_probe=_true_probe,
        celery_probe=lambda: True,
    )

    assert asyncio.run(ready_service.is_ready()) is True
    assert asyncio.run(unavailable_service.is_ready()) is False
