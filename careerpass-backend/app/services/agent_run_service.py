"""Application service for S-07 startup validation and context creation."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.infrastructure.database.models import AgentRunContext, JobGoal
from app.repositories.agent_run_repository import AgentRunRepository, StartPreconditions
from app.schemas.agent_run import (
    AgentRunStartResponse,
    AgentRunStatusResponse,
    AgentRunSummary,
)
from app.services.matching_service import MatchingService


class AgentRunPreconditionError(Exception):
    """The current candidate cannot start S-07 under the locked business rules."""


class AgentRunService:
    """Validate S-07 prerequisites and create only the downstream handoff context."""

    def __init__(
        self,
        *,
        repository: AgentRunRepository,
        matching_service: MatchingService | None = None,
    ) -> None:
        self._repository = repository
        self._matching_service = matching_service

    async def get_current(self, *, candidate_id: UUID) -> AgentRunStatusResponse:
        async with self._repository.transaction():
            conditions = await self._repository.get_start_preconditions(candidate_id=candidate_id)
        if conditions.run is not None:
            return AgentRunStatusResponse(
                state=conditions.run.status,
                can_start=False,
                run=_to_summary(conditions.run),
            )
        return AgentRunStatusResponse(
            state="not_started",
            can_start=_is_startable(conditions),
        )

    async def start(self, *, candidate_id: UUID) -> AgentRunStartResponse:
        run: AgentRunContext | None = None
        async with self._repository.transaction():
            conditions = await self._repository.get_start_preconditions(candidate_id=candidate_id)
            if conditions.run is not None:
                run = conditions.run
            else:
                if not _is_startable(conditions):
                    raise AgentRunPreconditionError
                assert conditions.goal is not None
                assert conditions.resume is not None
                assert conditions.profile is not None
                run = await self._repository.create_running(
                    candidate_id=candidate_id,
                    goal=conditions.goal,
                    resume=conditions.resume,
                    profile=conditions.profile,
                    goal_snapshot=_goal_snapshot(conditions.goal),
                )
        assert run is not None
        if self._matching_service is not None and run.status == "running":
            await self._matching_service.execute(run_id=run.id, candidate_id=candidate_id)
            async with self._repository.transaction():
                current = await self._repository.get_status(candidate_id=candidate_id)
            if current is not None:
                run = current
        return AgentRunStartResponse(run=_to_summary(run))


def _is_startable(conditions: StartPreconditions) -> bool:
    return (
        conditions.run is None
        and conditions.goal is not None
        and conditions.goal.status == "active"
        and conditions.resume_count == 1
        and conditions.resume is not None
        and conditions.resume.parse_status == "succeeded"
        and conditions.profile is not None
        and conditions.profile.matching_readiness == "matching_ready"
    )


def _to_summary(run: AgentRunContext) -> AgentRunSummary:
    return AgentRunSummary.model_validate(run, from_attributes=True)


def _goal_snapshot(goal: JobGoal) -> dict[str, object]:
    return {
        "id": str(goal.id),
        "offer_target": goal.offer_target,
        "title": goal.title,
        "filters": goal.filters,
        "status": goal.status,
        "created_at": _isoformat(goal.created_at),
        "updated_at": _isoformat(goal.updated_at),
    }


def _isoformat(value: datetime) -> str:
    return value.isoformat()
