"""Tests for Redis/Celery configuration and side-effect-free probe task."""

import asyncio

from celery import Celery

from app.infrastructure.cache import create_redis_client
from app.infrastructure.runtime import check_celery_configuration, check_database, check_redis
from app.infrastructure.tasks import create_celery_app


def test_redis_client_close_is_idempotent() -> None:
    redis_client = create_redis_client("redis://localhost:6379/15")

    asyncio.run(redis_client.close())
    asyncio.run(redis_client.close())

    assert redis_client._closed is True


def test_celery_probe_task_uses_safe_configuration_and_tracks_state() -> None:
    celery_app = create_celery_app(
        "redis://localhost:6379/15",
        task_time_limit_seconds=30,
        always_eager=True,
    )
    probe_task = celery_app.tasks["careerpass.runtime_probe"]
    result = probe_task.apply(args=({"idempotency_key": "probe-1"},))

    assert check_celery_configuration(celery_app) is True
    assert celery_app.conf.result_backend is None
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.broker_transport_options["visibility_timeout"] == 300
    assert probe_task.autoretry_for == (ConnectionError, TimeoutError)
    assert result.state == "SUCCESS"
    assert result.result == {"status": "succeeded", "idempotency_key": "probe-1"}


def test_celery_probe_task_rejects_invalid_input_without_side_effects() -> None:
    celery_app = create_celery_app(
        "redis://localhost:6379/15",
        task_time_limit_seconds=30,
        always_eager=True,
    )
    probe_task = celery_app.tasks["careerpass.runtime_probe"]
    result = probe_task.apply(args=({"idempotency_key": "contains spaces"},))

    assert result.state == "FAILURE"


def test_redis_readiness_probe_times_out_without_leaking_error() -> None:
    class SlowRedis:
        async def ping(self) -> bool:
            await asyncio.sleep(0.02)
            return True

    assert asyncio.run(check_redis(SlowRedis(), timeout_seconds=0.001)) is False


def test_database_and_redis_probes_fail_safely_on_connection_errors() -> None:
    class FailingEngine:
        def connect(self) -> None:
            raise ConnectionError("database unavailable")

    class FailingRedis:
        async def ping(self) -> bool:
            raise ConnectionError("redis unavailable")

    assert asyncio.run(check_database(FailingEngine(), timeout_seconds=0.1)) is False
    assert asyncio.run(check_redis(FailingRedis(), timeout_seconds=0.1)) is False


def test_database_and_redis_probes_succeed_for_healthy_dependencies() -> None:
    class HealthyConnection:
        async def __aenter__(self) -> "HealthyConnection":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def execute(self, _: object) -> None:
            return None

    class HealthyEngine:
        def connect(self) -> HealthyConnection:
            return HealthyConnection()

    class HealthyRedis:
        async def ping(self) -> bool:
            return True

    assert asyncio.run(check_database(HealthyEngine(), timeout_seconds=0.1)) is True
    assert asyncio.run(check_redis(HealthyRedis(), timeout_seconds=0.1)) is True


def test_celery_configuration_probe_rejects_incomplete_configuration() -> None:
    celery_app = Celery("incomplete")

    assert check_celery_configuration(celery_app) is False


def test_worker_entrypoint_uses_the_constrained_celery_configuration() -> None:
    from app.infrastructure.tasks.worker import celery_app

    assert check_celery_configuration(celery_app) is True
    assert "careerpass.runtime_probe" in celery_app.tasks
    assert "careerpass.resume_parse" in celery_app.tasks
