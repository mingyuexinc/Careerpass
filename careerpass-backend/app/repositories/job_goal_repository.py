"""Repository for candidate-owned current job goals."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import JobGoal


class JobGoalRepository:
    """Keep candidate ownership and current-goal persistence in one boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        return self._session.begin()

    async def get_current(self, *, candidate_id: UUID) -> JobGoal | None:
        return await self._session.scalar(
            select(JobGoal).where(JobGoal.candidate_id == candidate_id)
        )

    async def save_current(
        self,
        *,
        candidate_id: UUID,
        offer_target: int,
        title: str,
        filters: str,
    ) -> JobGoal:
        goal = await self.get_current(candidate_id=candidate_id)
        if goal is None:
            goal = JobGoal(
                candidate_id=candidate_id,
                offer_target=offer_target,
                title=title,
                filters=filters,
                status="active",
            )
            self._session.add(goal)
        else:
            goal.offer_target = offer_target
            goal.title = title
            goal.filters = filters
            goal.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return goal
