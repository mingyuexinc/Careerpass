"""Repository boundary for S-08 matching and candidate-safe applications."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AgentRunContext,
    Application,
    CandidateProfile,
    Conversation,
    Job,
    JobGoal,
    Match,
    ParsedJobDescriptionSnapshot,
    ProgressEvent,
)
from app.schemas.agent_run import AgentRunSummary
from app.schemas.application import ApplicationItem
from app.schemas.job_description import ParsedJobDescriptionFields
from app.services.matching_algorithm_v0_1 import (
    CandidateMatchingSummary,
    JobGoalMatchingSummary,
    JobMatchingSummary,
)


@dataclass(frozen=True)
class MatchingRunInput:
    run: AgentRunContext
    goal: JobGoalMatchingSummary
    candidate: CandidateMatchingSummary
    jobs: list[JobMatchingSummary]


@dataclass(frozen=True)
class ApplicationQueryResult:
    run: AgentRunSummary | None
    applications: list[ApplicationItem]


class MatchingRepository:
    """Own all S-08 persistence and Candidate/Run scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        return self._session.begin()

    async def load_run_input(self, *, run_id: UUID, candidate_id: UUID) -> MatchingRunInput | None:
        run = await self._session.scalar(
            select(AgentRunContext).where(
                AgentRunContext.id == run_id,
                AgentRunContext.candidate_id == candidate_id,
            ).with_for_update()
        )
        if run is None:
            return None
        goal = await self._session.scalar(
            select(JobGoal).where(
                JobGoal.id == run.job_goal_id,
                JobGoal.candidate_id == candidate_id,
            )
        )
        profile = await self._session.scalar(
            select(CandidateProfile).where(
                CandidateProfile.id == run.candidate_profile_id,
                CandidateProfile.resume_id == run.resume_id,
            )
        )
        if goal is None or profile is None:
            return None
        rows = (
            await self._session.execute(
                select(Job, ParsedJobDescriptionSnapshot)
                .join(ParsedJobDescriptionSnapshot, ParsedJobDescriptionSnapshot.job_id == Job.id)
                .where(Job.deleted_at.is_(None))
                .order_by(Job.created_at, Job.id)
                .limit(20)
            )
        ).all()
        jobs = [
            JobMatchingSummary(
                job_id=job.id,
                created_at=job.created_at,
                fields=ParsedJobDescriptionFields.model_validate(snapshot.fields),
            )
            for job, snapshot in rows
        ]
        candidate_data = CandidateMatchingSummary(
            target_job_titles=list(profile.target_job_titles or []),
            skills=_names(profile.skills),
            experience_titles=_experience_values(profile.work_experience_summary, "title"),
            experience_summaries=_experience_values(profile.work_experience_summary, "summary"),
            experience_highlights=_experience_highlights(profile.work_experience_summary),
            project_technologies=_project_technologies(profile.project_experience_summary),
            project_summaries=_experience_values(profile.project_experience_summary, "summary"),
            project_highlights=_experience_highlights(profile.project_experience_summary),
            years_of_experience=profile.years_of_experience,
        )
        return MatchingRunInput(
            run=run,
            goal=JobGoalMatchingSummary(title=goal.title, filters=goal.filters),
            candidate=candidate_data,
            jobs=jobs,
        )

    async def get_match(self, *, run_id: UUID, job_id: UUID) -> Match | None:
        return await self._session.scalar(
            select(Match).where(Match.run_id == run_id, Match.job_id == job_id).with_for_update()
        )

    async def create_match(self, *, run_id: UUID, candidate_id: UUID, job_id: UUID,
                           algorithm_version: str, result: object) -> Match:
        value = Match(
            run_id=run_id,
            candidate_id=candidate_id,
            job_id=job_id,
            algorithm_version=algorithm_version,
            input_snapshot=result.input_snapshot,
            status=result.status,
            role_score=result.role_score,
            level_score=result.level_score,
            skill_score=result.skill_score,
            total_score=result.total_score,
            recommendation_reason=result.recommendation_reason,
            reason_code=result.reason_code,
        )
        self._session.add(value)
        await self._session.flush()
        return value

    async def ensure_application(self, *, match: Match) -> Application:
        application = await self._session.scalar(
            select(Application).where(
                Application.run_id == match.run_id,
                Application.job_id == match.job_id,
            ).with_for_update()
        )
        if application is not None:
            if match.status == "matched":
                match.status = "application_created"
            await self.ensure_conversation(application_id=application.id)
            return application
        now = datetime.now(UTC)
        application = Application(
            run_id=match.run_id,
            match_id=match.id,
            candidate_id=match.candidate_id,
            job_id=match.job_id,
            status="submitted",
            applied_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(application)
        await self._session.flush()
        self._session.add(
            ProgressEvent(
                application_id=application.id,
                candidate_id=match.candidate_id,
                job_id=match.job_id,
                event_type="application_created",
                from_status=None,
                to_status="submitted",
                actor="agent",
                created_at=now,
            )
        )
        match.status = "application_created"
        await self._session.flush()
        await self.ensure_conversation(application_id=application.id)
        return application

    async def ensure_conversation(self, *, application_id: UUID) -> Conversation:
        """Create the single current Conversation container for an Application."""
        conversation = await self._session.scalar(
            select(Conversation).where(Conversation.application_id == application_id).with_for_update()
        )
        if conversation is not None:
            return conversation
        conversation = Conversation(application_id=application_id)
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def count_applications(self, *, run_id: UUID, candidate_id: UUID) -> int:
        from sqlalchemy import func

        return int(await self._session.scalar(
            select(func.count(Application.id)).where(
                Application.run_id == run_id,
                Application.candidate_id == candidate_id,
            )
        ) or 0)

    async def finish_no_match(self, *, run_id: UUID, candidate_id: UUID) -> AgentRunContext | None:
        run = await self._session.scalar(
            select(AgentRunContext).where(
                AgentRunContext.id == run_id,
                AgentRunContext.candidate_id == candidate_id,
            ).with_for_update()
        )
        if run is not None and run.status == "running":
            run.status = "finished"
            run.finish_reason = "no_match"
            run.finished_at = datetime.now(UTC)
            await self._session.flush()
        return run

    async def list_current_applications(self, *, candidate_id: UUID) -> ApplicationQueryResult:
        run = await self._session.scalar(
            select(AgentRunContext)
            .where(AgentRunContext.candidate_id == candidate_id)
            .order_by(desc(AgentRunContext.created_at), desc(AgentRunContext.id))
            .limit(1)
        )
        if run is None:
            return ApplicationQueryResult(run=None, applications=[])
        rows = (
            await self._session.execute(
                select(Application, Job, ParsedJobDescriptionSnapshot, Match)
                .join(Job, Job.id == Application.job_id)
                .join(ParsedJobDescriptionSnapshot, ParsedJobDescriptionSnapshot.job_id == Job.id)
                .join(Match, Match.id == Application.match_id)
                .where(
                    Application.candidate_id == candidate_id,
                    Application.run_id == run.id,
                )
                .order_by(desc(Match.total_score), Application.applied_at, Application.job_id)
            )
        ).all()
        applications = [
            _application_item(application, job, snapshot, match)
            for application, job, snapshot, match in rows
        ]
        return ApplicationQueryResult(
            run=AgentRunSummary.model_validate(run, from_attributes=True),
            applications=applications,
        )


def _application_item(application: Application, job: Job,
                      snapshot: ParsedJobDescriptionSnapshot, match: Match) -> ApplicationItem:
    fields = ParsedJobDescriptionFields.model_validate(snapshot.fields)
    company = fields.company_name
    return ApplicationItem(
        id=application.id,
        job_id=job.id,
        candidate_id=application.candidate_id,
        status=application.status,
        job_title=fields.title.normalized or fields.title.raw,
        company_name=(company.normalized or company.raw) if company else None,
        location=fields.location.normalized or fields.location.raw,
        salary=fields.salary_range.raw,
        match_score=round(match.total_score or 0),
        recommendation_reason=match.recommendation_reason,
        applied_at=application.applied_at,
    )


def _names(values: list[dict[str, object]] | None) -> list[str]:
    return [str(value.get("name", "")) for value in values or [] if str(value.get("name", "")).strip()]


def _experience_values(values: list[dict[str, object]] | None, key: str) -> list[str]:
    return [str(value.get(key, "")) for value in values or [] if str(value.get(key, "")).strip()]


def _experience_highlights(values: list[dict[str, object]] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        highlights = value.get("highlights", [])
        if isinstance(highlights, list):
            result.extend(str(item) for item in highlights if str(item).strip())
    return result


def _project_technologies(values: list[dict[str, object]] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        result.extend(str(item) for item in value.get("technologies", []) if str(item).strip())
    return result
