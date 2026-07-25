"""Async Redis client lifecycle management."""

from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass
class RedisClient:
    """Own a Redis client and close it safely during application shutdown."""

    client: Redis
    _closed: bool = False

    async def close(self) -> None:
        """Close the underlying connection pool; repeated calls are safe."""
        if self._closed:
            return
        await self.client.aclose()
        self._closed = True


def create_redis_client(redis_url: str) -> RedisClient:
    """Build a Redis client without opening a connection."""
    return RedisClient(client=Redis.from_url(redis_url, decode_responses=False))
