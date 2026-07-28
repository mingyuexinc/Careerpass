"""Timeout-bounded probes for external runtime dependencies."""

import asyncio

from celery import Celery
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def check_database(engine: AsyncEngine, timeout_seconds: float) -> bool:
    """Return whether PostgreSQL is reachable without leaking the failure reason."""
    try:
        async with asyncio.timeout(timeout_seconds):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis(redis_client: Redis, timeout_seconds: float) -> bool:
    """Return whether Redis is reachable without leaking the failure reason."""
    try:
        async with asyncio.timeout(timeout_seconds):
            await redis_client.ping()
        return True
    except Exception:
        return False


def check_celery_configuration(celery_app: Celery) -> bool:
    """Verify Celery's local safe configuration without contacting a worker."""
    return bool(
        celery_app.conf.broker_url
        and celery_app.conf.result_backend is None
        and celery_app.conf.task_track_started
        and celery_app.conf.task_serializer == "json"
        and celery_app.conf.result_serializer == "json"
        and celery_app.conf.task_acks_late
        and celery_app.conf.task_reject_on_worker_lost
        and celery_app.conf.worker_prefetch_multiplier == 1
    )
