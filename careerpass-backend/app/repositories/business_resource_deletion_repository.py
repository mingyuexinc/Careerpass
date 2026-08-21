from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AgentRunContext,
    Application,
    AsyncTaskRun,
    Candidate,
    CandidateDocument,
    Job,
    Match,
    ParsedJobDescriptionSnapshot,
    ResourceAuditEvent,
    Resume,
)


class DeletionResourceNotFoundError(Exception):
    """The requested resource does not exist."""


class DeletionOwnershipError(Exception):
    """The resource exists but is not owned by the active identity."""


class DeletionNotAllowedError(Exception):
    """The resource exists but its current state cannot be deleted."""


@dataclass(frozen=True)
class ResourceDeletionResult:
    resource_type: str
    resource_id: UUID
    deleted: bool


class BusinessResourceDeletionRepository:
    """Own S-11 resource locks, state checks, logical deletion and audit writes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        return self._session.begin()

    async def delete_resume(
        self, *, candidate_id: UUID, resume_id: UUID, actor_user_id: UUID, actor_role: str
    ) -> ResourceDeletionResult:
        async with self._session.begin():
            resume = await self._session.scalar(
                select(Resume).where(Resume.id == resume_id).with_for_update()
            )
            if resume is None:
                raise DeletionResourceNotFoundError
            if resume.candidate_id != candidate_id:
                raise DeletionOwnershipError
            if resume.deleted_at is not None:
                return ResourceDeletionResult("resume", resume.id, False)

            candidate = await self._session.scalar(
                select(Candidate).where(Candidate.id == candidate_id).with_for_update()
            )
            if candidate is None:
                raise DeletionOwnershipError
            if candidate.current_resume_id != resume.id:
                raise DeletionNotAllowedError("only the current resume can be deleted")
            if resume.parse_status not in {"succeeded", "failed"}:
                raise DeletionNotAllowedError("resume parsing is not complete")
            if await self._agent_started(candidate_id):
                raise DeletionNotAllowedError("agent has already started")

            resume.deleted_at = datetime.now(UTC)
            candidate.current_resume_id = None
            await self._record_audit(
                resource_type="resume",
                resource_id=resume.id,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
            )
        return ResourceDeletionResult("resume", resume.id, True)

    async def delete_candidate_document(
        self,
        *,
        candidate_id: UUID,
        document_id: UUID,
        actor_user_id: UUID,
        actor_role: str,
    ) -> ResourceDeletionResult:
        async with self._session.begin():
            document = await self._session.scalar(
                select(CandidateDocument).where(CandidateDocument.id == document_id).with_for_update()
            )
            if document is None:
                raise DeletionResourceNotFoundError
            if document.candidate_id != candidate_id:
                raise DeletionOwnershipError
            if document.deleted_at is not None:
                return ResourceDeletionResult("candidate_document", document.id, False)

            document.deleted_at = datetime.now(UTC)
            await self._record_audit(
                resource_type="candidate_document",
                resource_id=document.id,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
            )
        return ResourceDeletionResult("candidate_document", document.id, True)

    async def delete_job(
        self, *, hr_profile_id: UUID, job_id: UUID, actor_user_id: UUID, actor_role: str
    ) -> ResourceDeletionResult:
        async with self._session.begin():
            job = await self._session.scalar(
                select(Job).where(Job.id == job_id).with_for_update()
            )
            if job is None:
                raise DeletionResourceNotFoundError
            if job.hr_profile_id != hr_profile_id:
                raise DeletionOwnershipError
            if job.deleted_at is not None:
                return ResourceDeletionResult("job", job.id, False)

            task = await self._session.scalar(
                select(AsyncTaskRun)
                .where(
                    AsyncTaskRun.resource_type == "job",
                    AsyncTaskRun.resource_id == job.id,
                    AsyncTaskRun.task_type == "job_jd_parse",
                )
                .order_by(AsyncTaskRun.created_at.desc(), AsyncTaskRun.id.desc())
                .limit(1)
                .with_for_update()
            )
            if task is None or task.status not in {"succeeded", "failed"}:
                raise DeletionNotAllowedError("job parsing is not complete")
            if await self._job_has_matching_reference(job.id):
                raise DeletionNotAllowedError("job matching has already started")

            job.deleted_at = datetime.now(UTC)
            await self._session.execute(
                delete(ParsedJobDescriptionSnapshot).where(
                    ParsedJobDescriptionSnapshot.job_id == job.id
                )
            )
            await self._record_audit(
                resource_type="job",
                resource_id=job.id,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
            )
        return ResourceDeletionResult("job", job.id, True)

    async def _agent_started(self, candidate_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists(
                        select(1).where(AgentRunContext.candidate_id == candidate_id)
                    )
                )
            )
        )

    async def _job_has_matching_reference(self, job_id: UUID) -> bool:
        match_exists = await self._session.scalar(
            select(exists(select(1).where(Match.job_id == job_id)))
        )
        if match_exists:
            return True
        return bool(
            await self._session.scalar(
                select(exists(select(1).where(Application.job_id == job_id)))
            )
        )

    async def _record_audit(
        self,
        *,
        resource_type: str,
        resource_id: UUID,
        actor_user_id: UUID,
        actor_role: str,
    ) -> None:
        self._session.add(
            ResourceAuditEvent(
                resource_type=resource_type,
                resource_id=resource_id,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                event_type="resource_deleted",
            )
        )
