"""Repository for resolving candidate ownership from trusted identity inputs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Candidate


class CandidateRepository:
    """Own candidate lookups used to enforce user-level ownership checks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, candidate_id: UUID) -> Candidate | None:
        """Return a candidate by its primary key."""
        result = await self._session.execute(select(Candidate).where(Candidate.id == candidate_id))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Candidate | None:
        """Resolve the unique candidate associated with a trusted user identity."""
        result = await self._session.execute(select(Candidate).where(Candidate.user_id == user_id))
        return result.scalar_one_or_none()
