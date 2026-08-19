"""Repository boundary for HR-facing Application queries and updates."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.infrastructure.database.models import (
    AgentRunContext,
    Application,
    CandidateProfile,
    Job,
    JobGoal,
    ParsedJobDescriptionSnapshot,
    ProgressEvent,
)
from app.schemas.application import HrApplicationItem
from app.schemas.job_description import ParsedJobDescriptionFields


@dataclass(frozen=True)
class HrApplicationRecord:
    """Locked Application aggregate and data needed for its HR projection."""

    application: Application
    job: Job
    snapshot: ParsedJobDescriptionSnapshot
    profile: CandidateProfile
    run: AgentRunContext
    goal: JobGoal


class ApplicationRepository:
    """Own HR Application persistence, scoping, locking, and projection assembly."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        return self._session.begin()

    async def list_current_for_hr(self, *, hr_profile_id: UUID) -> list[HrApplicationItem]:
        run = AgentRunContext
        latest_run = aliased(AgentRunContext)
        latest_run_id = (
            select(latest_run.id)
            .order_by(desc(latest_run.created_at), desc(latest_run.id))
            .limit(1)
            .scalar_subquery()
        )
        rows = (
            await self._session.execute(
                select(Application, Job, ParsedJobDescriptionSnapshot, CandidateProfile, run)
                .join(Job, Job.id == Application.job_id)
                .join(run, run.id == Application.run_id)
                .join(
                    ParsedJobDescriptionSnapshot,
                    ParsedJobDescriptionSnapshot.job_id == Job.id,
                )
                .join(CandidateProfile, CandidateProfile.id == run.candidate_profile_id)
                .where(
                    Job.hr_profile_id == hr_profile_id,
                    Job.deleted_at.is_(None),
                    Application.candidate_id == run.candidate_id,
                    CandidateProfile.resume_id == run.resume_id,
                    run.id == latest_run_id,
                    CandidateProfile.full_name.is_not(None),
                    CandidateProfile.full_name != "",
                )
                .order_by(Job.created_at, Application.applied_at, Application.id)
            )
        ).all()
        return [
            _to_hr_item(
                application=application,
                job=job,
                snapshot=snapshot,
                profile=profile,
            )
            for application, job, snapshot, profile, _ in rows
        ]

    async def get_for_hr_update(
        self,
        *,
        application_id: UUID,
        hr_profile_id: UUID,
    ) -> HrApplicationRecord | None:
        run = AgentRunContext
        latest_run = aliased(AgentRunContext)
        latest_run_id = (
            select(latest_run.id)
            .order_by(desc(latest_run.created_at), desc(latest_run.id))
            .limit(1)
            .scalar_subquery()
        )
        row = (
            await self._session.execute(
                select(
                    Application,
                    Job,
                    ParsedJobDescriptionSnapshot,
                    CandidateProfile,
                    run,
                    JobGoal,
                )
                .join(Job, Job.id == Application.job_id)
                .join(run, run.id == Application.run_id)
                .join(
                    ParsedJobDescriptionSnapshot,
                    ParsedJobDescriptionSnapshot.job_id == Job.id,
                )
                .join(CandidateProfile, CandidateProfile.id == run.candidate_profile_id)
                .join(JobGoal, JobGoal.id == run.job_goal_id)
                .where(
                    Application.id == application_id,
                    Job.hr_profile_id == hr_profile_id,
                    Job.deleted_at.is_(None),
                    Application.candidate_id == run.candidate_id,
                    CandidateProfile.resume_id == run.resume_id,
                    JobGoal.candidate_id == run.candidate_id,
                    run.id == latest_run_id,
                    CandidateProfile.full_name.is_not(None),
                    CandidateProfile.full_name != "",
                )
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            return None
        application, job, snapshot, profile, current_run, goal = row
        await self._lock_run_and_goal(run_id=current_run.id, goal_id=goal.id)
        return HrApplicationRecord(
            application=application,
            job=job,
            snapshot=snapshot,
            profile=profile,
            run=current_run,
            goal=goal,
        )

    async def count_offers(self, *, run_id: UUID, candidate_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count(Application.id)).where(
                    Application.run_id == run_id,
                    Application.candidate_id == candidate_id,
                    Application.status == "offer",
                )
            )
            or 0
        )

    async def append_status_event(
        self,
        *,
        record: HrApplicationRecord,
        from_status: str,
        to_status: str,
        now: datetime,
    ) -> None:
        self._session.add(
            ProgressEvent(
                application_id=record.application.id,
                candidate_id=record.application.candidate_id,
                job_id=record.application.job_id,
                event_type="application_status_updated",
                from_status=from_status,
                to_status=to_status,
                actor="hr",
                created_at=now,
            )
        )
        await self._session.flush()

    async def finish_for_offer_target(
        self,
        *,
        record: HrApplicationRecord,
        offer_count: int,
        now: datetime,
    ) -> None:
        if record.run.status == "running" and offer_count >= record.goal.offer_target:
            record.run.status = "finished"
            record.run.finish_reason = "offer_target_reached"
            record.run.finished_at = now
            record.goal.status = "achieved"
            record.goal.updated_at = now

    async def _lock_run_and_goal(self, *, run_id: UUID, goal_id: UUID) -> None:
        await self._session.scalar(
            select(AgentRunContext).where(AgentRunContext.id == run_id).with_for_update()
        )
        await self._session.scalar(
            select(JobGoal).where(JobGoal.id == goal_id).with_for_update()
        )


def to_hr_item(record: HrApplicationRecord) -> HrApplicationItem:
    return _to_hr_item(
        application=record.application,
        job=record.job,
        snapshot=record.snapshot,
        profile=record.profile,
    )


def _to_hr_item(
    *,
    application: Application,
    job: Job,
    snapshot: ParsedJobDescriptionSnapshot,
    profile: CandidateProfile,
) -> HrApplicationItem:
    fields = ParsedJobDescriptionFields.model_validate(snapshot.fields)
    title = fields.title.normalized or fields.title.raw
    company = fields.company_name
    return HrApplicationItem(
        id=application.id,
        job_id=job.id,
        job_title=title,
        company_name=(company.normalized or company.raw) if company else None,
        candidate_name=profile.full_name or "",
        status=application.status,
    )
