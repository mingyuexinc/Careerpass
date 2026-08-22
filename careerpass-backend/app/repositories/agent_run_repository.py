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
    Application,
    AsyncTaskRun,
    Candidate,
    CandidateProfile,
    Job,
    JobGoal,
    ParsedJobDescriptionSnapshot,
    Resume,
)


@dataclass(frozen=True)
class StartPreconditions:
    goal: JobGoal | None
    resume: Resume | None
    resume_count: int
    profile: CandidateProfile | None
    run: AgentRunContext | None
    active_job_count: int = 0
    eligible_job_count: int = 1
    pending_job_count: int = 0
    failed_job_count: int = 0
    restartable: bool = False


@dataclass(frozen=True)
class JobReadiness:
    active_job_count: int
    eligible_job_count: int
    pending_job_count: int
    failed_job_count: int


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
            .order_by(AgentRunContext.created_at.desc(), AgentRunContext.id.desc())
            .limit(1)
        )
        restartable = False
        if (
            run is not None
            and run.status == "finished"
            and run.finish_reason == "no_match"
        ):
            application_count = int(
                await self._session.scalar(
                    select(func.count())
                    .select_from(Application)
                    .where(
                        Application.run_id == run.id,
                        Application.candidate_id == candidate_id,
                    )
                )
                or 0
            )
            restartable = application_count == 0
        readiness = await self.get_job_readiness()
        return StartPreconditions(
            goal,
            resume,
            resume_count,
            profile,
            run,
            readiness.active_job_count,
            readiness.eligible_job_count,
            readiness.pending_job_count,
            readiness.failed_job_count,
            restartable,
        )

    async def get_job_readiness(self) -> JobReadiness:
        rows = (
            await self._session.execute(
                select(Job.id, ParsedJobDescriptionSnapshot.id)
                .outerjoin(
                    ParsedJobDescriptionSnapshot,
                    ParsedJobDescriptionSnapshot.job_id == Job.id,
                )
                .where(Job.deleted_at.is_(None))
            )
        ).all()
        task_rows = (
            await self._session.execute(
                select(AsyncTaskRun)
                .where(
                    AsyncTaskRun.task_type == "job_jd_parse",
                    AsyncTaskRun.resource_type == "job",
                )
                .order_by(
                    AsyncTaskRun.task_generation.desc(),
                    AsyncTaskRun.created_at.desc(),
                    AsyncTaskRun.id.desc(),
                )
            )
        ).scalars().all()
        latest_tasks: dict[UUID, AsyncTaskRun] = {}
        for task in task_rows:
            latest_tasks.setdefault(task.resource_id, task)
        eligible = pending = failed = 0
        for job_id, snapshot_id in rows:
            task = latest_tasks.get(job_id)
            if task is not None and task.status == "succeeded" and snapshot_id is not None:
                eligible += 1
            elif task is None or task.status in {"queued", "running"}:
                pending += 1
            elif task.status == "failed":
                failed += 1
        return JobReadiness(
            active_job_count=len(rows),
            eligible_job_count=eligible,
            pending_job_count=pending,
            failed_job_count=failed,
        )

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
