"""Async PostgreSQL engine and session-factory lifecycle management."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass
class Database:
    """Own the engine and session factory; only infrastructure may construct it."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    _closed: bool = False

    async def close(self) -> None:
        """Dispose engine resources; repeated shutdown calls are safe."""
        if self._closed:
            return
        await self.engine.dispose()
        self._closed = True


def create_database(database_url: str, *, pool_size: int = 5) -> Database:
    """Build an async PostgreSQL engine without making a database connection."""
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=0,
    )
    return Database(
        engine=engine,
        session_factory=async_sessionmaker(engine, expire_on_commit=False),
    )
