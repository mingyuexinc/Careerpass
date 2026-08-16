"""Repository operations for the development-only current-account reset."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.identity import CurrentIdentity
from app.infrastructure.database.models import (
    AsyncTaskRun,
    Candidate,
    CandidateDocument,
    CandidateProfile,
    HrProfile,
    Job,
    JobGoal,
    ParsedJobDescriptionSnapshot,
    Resume,
    StoredFileObject,
)
from app.repositories.object_storage_repository import CleanupClaim


class ResetAccountBusyError(Exception):
    """Raised when an account still owns queued or running work."""


class ResetAccountConflictError(Exception):
    """Raised when a safe account-scoped reset is blocked by dependencies."""


@dataclass(frozen=True)
class ResetResources:
    """Physical objects that can be removed after the database transaction."""

    storage_claims: tuple[CleanupClaim, ...]


class DebugResetRepository:
    """Own the account-scoped reset transaction and ownership predicates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self._session.begin():
                yield
        except IntegrityError:
            raise ResetAccountConflictError from None

    async def reset_current_account(self, identity: CurrentIdentity) -> ResetResources:
        if identity.active_role == "candidate":
            if identity.candidate_id is None:
                raise ResetAccountConflictError
            return await self._reset_candidate(identity.candidate_id)
        if identity.hr_profile_id is None:
            raise ResetAccountConflictError
        return await self._reset_hr(identity.hr_profile_id)

    async def _reset_candidate(self, candidate_id: UUID) -> ResetResources:
        candidate = await self._session.scalar(
            select(Candidate).where(Candidate.id == candidate_id).with_for_update()
        )
        if candidate is None:
            raise ResetAccountConflictError

        resumes = list(
            (
                await self._session.scalars(
                    select(Resume).where(Resume.candidate_id == candidate_id)
                )
            ).all()
        )
        documents = list(
            (
                await self._session.scalars(
                    select(CandidateDocument).where(CandidateDocument.candidate_id == candidate_id)
                )
            ).all()
        )
        resume_ids = tuple(value.id for value in resumes)
        await self._assert_no_active_tasks(resource_type="resume", resource_ids=resume_ids)

        file_ids = {value.stored_file_object_id for value in resumes}
        file_ids.update(value.stored_file_object_id for value in documents)
        if resume_ids:
            profiles = list(
                (
                    await self._session.scalars(
                        select(CandidateProfile).where(CandidateProfile.resume_id.in_(resume_ids))
                    )
                ).all()
            )
            for profile in profiles:
                await self._session.delete(profile)
            for task in await self._task_rows(resource_type="resume", resource_ids=resume_ids):
                await self._session.delete(task)
        for document in documents:
            await self._session.delete(document)
        for resume in resumes:
            await self._session.delete(resume)

        goal = await self._session.scalar(
            select(JobGoal).where(JobGoal.candidate_id == candidate_id)
        )
        if goal is not None:
            await self._session.delete(goal)
        await self._session.flush()
        return ResetResources(storage_claims=await self._claim_unreferenced(file_ids))

    async def _reset_hr(self, hr_profile_id: UUID) -> ResetResources:
        hr_profile = await self._session.scalar(
            select(HrProfile).where(HrProfile.id == hr_profile_id).with_for_update()
        )
        if hr_profile is None:
            raise ResetAccountConflictError

        jobs = list(
            (
                await self._session.scalars(
                    select(Job).where(Job.hr_profile_id == hr_profile_id)
                )
            ).all()
        )
        job_ids = tuple(value.id for value in jobs)
        await self._assert_no_active_tasks(resource_type="job", resource_ids=job_ids)
        file_ids = {value.stored_file_object_id for value in jobs}

        if job_ids:
            snapshots = list(
                (
                    await self._session.scalars(
                        select(ParsedJobDescriptionSnapshot).where(
                            ParsedJobDescriptionSnapshot.job_id.in_(job_ids)
                        )
                    )
                ).all()
            )
            for snapshot in snapshots:
                await self._session.delete(snapshot)
            for task in await self._task_rows(resource_type="job", resource_ids=job_ids):
                await self._session.delete(task)
        for job in jobs:
            await self._session.delete(job)
        await self._session.flush()
        return ResetResources(storage_claims=await self._claim_unreferenced(file_ids))

    async def _assert_no_active_tasks(
        self, *, resource_type: str, resource_ids: tuple[UUID, ...]
    ) -> None:
        if not resource_ids:
            return
        active = await self._session.scalar(
            select(
                exists(
                    select(1).where(
                        AsyncTaskRun.resource_type == resource_type,
                        AsyncTaskRun.resource_id.in_(resource_ids),
                        AsyncTaskRun.status.in_(("queued", "running")),
                    )
                )
            )
        )
        if active:
            raise ResetAccountBusyError

    async def _task_rows(
        self, *, resource_type: str, resource_ids: tuple[UUID, ...]
    ) -> list[AsyncTaskRun]:
        if not resource_ids:
            return []
        return list(
            (
                await self._session.scalars(
                    select(AsyncTaskRun).where(
                        AsyncTaskRun.resource_type == resource_type,
                        AsyncTaskRun.resource_id.in_(resource_ids),
                    )
                )
            ).all()
        )

    async def _claim_unreferenced(self, file_ids: set[UUID]) -> tuple[CleanupClaim, ...]:
        claims: list[CleanupClaim] = []
        for file_id in file_ids:
            value = await self._session.scalar(
                select(StoredFileObject).where(StoredFileObject.id == file_id).with_for_update()
            )
            if value is None or await self._has_reference(value.id):
                continue
            value.status = "deleting"
            claims.append(
                CleanupClaim(
                    object_id=value.id,
                    storage_key=value.storage_key,
                    previous_status="deleting",
                )
            )
        await self._session.flush()
        return tuple(claims)

    async def _has_reference(self, object_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists(
                        select(1).where(
                            or_(
                                Resume.stored_file_object_id == object_id,
                                CandidateDocument.stored_file_object_id == object_id,
                                Job.stored_file_object_id == object_id,
                            )
                        )
                    )
                )
            )
        )
