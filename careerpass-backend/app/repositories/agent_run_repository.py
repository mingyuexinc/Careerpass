"""Repository boundary for candidate-owned S-07 Agent startup contexts."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AgentRunContext,
    Candidate,
    CandidateProfile,
    JobGoal,
    Resume,
)


@dataclass(frozen=True)
class StartPreconditions:
    goal: JobGoal | None
    resume: Resume | None
    resume_count: int
    profile: CandidateProfile | None
    run: AgentRunContext | None


class AgentRunRepository:
    """Own startup locking, candidate scoping, and AgentRunContext persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        return self._session.begin()

    async def get_status(self, *, candidate_id: UUID) -> AgentRunContext | None:
        return await self._session.scalar(
            select(AgentRunContext)
            .where(AgentRunContext.candidate_id == candidate_id)
            .order_by(AgentRunContext.created_at.desc(), AgentRunContext.id.desc())
            .limit(1)
        )

    async def get_start_preconditions(self, *, candidate_id: UUID) -> StartPreconditions:
        goal = await self._session.scalar(
            select(JobGoal)
            .where(JobGoal.candidate_id == candidate_id)
            .with_for_update()
        )
        resume_count = int(
            await self._session.scalar(
                select(func.count())
                .select_from(Resume)
                .where(Resume.candidate_id == candidate_id, Resume.deleted_at.is_(None))
            )
            or 0
        )
        resume = None
        profile = None
        candidate = await self._session.scalar(
            select(Candidate).where(Candidate.id == candidate_id).with_for_update()
        )
        if candidate is not None and candidate.current_resume_id is not None:
            resume = await self._session.scalar(
                select(Resume).where(
                    Resume.id == candidate.current_resume_id,
                    Resume.candidate_id == candidate_id,
                    Resume.deleted_at.is_(None),
                )
            )
            if resume is not None:
                profile = await self._session.scalar(
                    select(CandidateProfile)
                    .where(CandidateProfile.resume_id == resume.id)
                )
        run = await self._session.scalar(
            select(AgentRunContext)
            .where(
                AgentRunContext.candidate_id == candidate_id,
                AgentRunContext.job_goal_id == goal.id if goal is not None else False,
            )
        )
        return StartPreconditions(goal, resume, resume_count, profile, run)

    async def create_running(
        self,
        *,
        candidate_id: UUID,
        goal: JobGoal,
        resume: Resume,
        profile: CandidateProfile,
        goal_snapshot: dict[str, object],
    ) -> AgentRunContext:
        value = AgentRunContext(
            candidate_id=candidate_id,
            job_goal_id=goal.id,
            resume_id=resume.id,
            candidate_profile_id=profile.id,
            goal_snapshot=goal_snapshot,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(value)
        await self._session.flush()
        return value
