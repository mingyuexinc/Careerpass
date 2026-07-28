"""Unit tests for Redis-backed authentication rate limiting."""

import asyncio
from types import SimpleNamespace

from redis.exceptions import ConnectionError as RedisConnectionError

from app.api.dependencies.rate_limit import enforce_auth_rate_limit
from app.core.config import Settings
from app.core.exceptions import AppException


class CountingRedis:
    """Small Redis double that verifies the limiter uses atomic script execution."""

    def __init__(self, attempts: int) -> None:
        self.attempts = attempts
        self.calls: list[tuple[object, ...]] = []

    async def eval(self, *args: object) -> int:
        self.calls.append(args)
        return self.attempts


class FailingRedis:
    """Redis double for fail-closed limiter behavior."""

    async def eval(self, *args: object) -> int:
        raise RedisConnectionError


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql+asyncpg://test:test@localhost:5432/test",
        "redis_url": "redis://localhost:6379/15",
        "jwt_secret_key": "test-jwt-secret-key-with-at-least-32-characters",
        "auth_rate_limit_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)


def _request(redis_client: object) -> SimpleNamespace:
    return SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        url=SimpleNamespace(path="/api/v1/auth/login"),
        app=SimpleNamespace(
            state=SimpleNamespace(redis_client=SimpleNamespace(client=redis_client))
        ),
    )


def test_auth_rate_limit_allows_attempts_at_or_below_the_configured_limit() -> None:
    redis = CountingRedis(attempts=3)

    asyncio.run(enforce_auth_rate_limit(_request(redis), _settings(auth_rate_limit_requests=3)))

    assert len(redis.calls) == 1
    assert redis.calls[0][1] == 1


def test_auth_rate_limit_rejects_excessive_attempts() -> None:
    redis = CountingRedis(attempts=4)

    try:
        asyncio.run(enforce_auth_rate_limit(_request(redis), _settings(auth_rate_limit_requests=3)))
    except AppException as exc:
        assert exc.status_code == 429
        assert exc.code.value == 429
        assert exc.message == "too many authentication attempts"
    else:
        raise AssertionError("expected rate limit rejection")


def test_auth_rate_limit_fails_closed_when_redis_is_unavailable() -> None:
    try:
        asyncio.run(enforce_auth_rate_limit(_request(FailingRedis()), _settings()))
    except AppException as exc:
        assert exc.status_code == 503
        assert exc.message == "authentication temporarily unavailable"
    else:
        raise AssertionError("expected safe dependency failure")


def test_auth_rate_limit_can_be_disabled_outside_production() -> None:
    asyncio.run(
        enforce_auth_rate_limit(
            _request(FailingRedis()),
            _settings(auth_rate_limit_enabled=False),
        )
    )
