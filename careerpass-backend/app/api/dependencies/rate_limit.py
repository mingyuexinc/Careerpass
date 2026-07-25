"""Redis-backed rate limiting for authentication endpoints."""

import asyncio
from typing import Annotated

from fastapi import Depends, Request, status
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode
from app.core.exceptions import AppException

_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


async def enforce_auth_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject excessive authentication attempts without exposing limiter details."""
    if not settings.auth_rate_limit_enabled:
        return

    client_host = request.client.host if request.client is not None else "unknown"
    key = f"auth-rate-limit:{request.url.path}:{client_host}"
    try:
        async with asyncio.timeout(settings.auth_rate_limit_timeout_seconds):
            attempts = await request.app.state.redis_client.client.eval(
                _INCREMENT_WITH_EXPIRY,
                1,
                key,
                settings.auth_rate_limit_window_seconds,
            )
    except (RedisError, TimeoutError):
        raise AppException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.INTERNAL_ERROR,
            message="authentication temporarily unavailable",
        ) from None

    if int(attempts) > settings.auth_rate_limit_requests:
        raise AppException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code=ErrorCode.TOO_MANY_REQUESTS,
            message="too many authentication attempts",
        )
