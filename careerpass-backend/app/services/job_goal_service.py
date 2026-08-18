"""Application service for S-06 current job-goal creation and update."""

from __future__ import annotations

from uuid import UUID

from app.infrastructure.database.models import JobGoal
from app.repositories.job_goal_repository import JobGoalRepository
from app.schemas.job_goal import CurrentJobGoalResponse, JobGoalInput, JobGoalResponse


class JobGoalLockedError(Exception):
    """The current goal is no longer editable by S-06."""


class JobGoalService:
    """Coordinate validated goal input and candidate-owned persistence."""

    def __init__(self, *, repository: JobGoalRepository) -> None:
        self._repository = repository

    async def get_current(self, *, candidate_id: UUID) -> CurrentJobGoalResponse:
        goal = await self._repository.get_current(candidate_id=candidate_id)
        return CurrentJobGoalResponse(goal=_to_response(goal) if goal else None)

    async def save_current(
        self, *, candidate_id: UUID, value: JobGoalInput
    ) -> JobGoalResponse:
        async with self._repository.transaction():
            if await self._repository.has_locked_run(candidate_id=candidate_id):
                raise JobGoalLockedError
            existing = await self._repository.get_current(candidate_id=candidate_id)
            if existing is not None and existing.status != "active":
                raise JobGoalLockedError
            goal = await self._repository.save_current(
                candidate_id=candidate_id,
                offer_target=value.offer_target,
                title=value.title,
                filters=value.filters,
            )
        return _to_response(goal)


def _to_response(goal: JobGoal) -> JobGoalResponse:
    return JobGoalResponse.model_validate(goal, from_attributes=True)
