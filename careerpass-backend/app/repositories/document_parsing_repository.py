"""Repository boundary for resume parsing requests, profiles, and terminal writes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AsyncTaskRun,
    CandidateProfile,
    Resume,
    StoredFileObject,
)
from app.schemas.document_parsing import (
    ParseFailureCode,
    ResumeParseRequestV1,
    ResumeProfileExtractionV1,
    matching_readiness,
)


class ResumeStorageUnavailableError(Exception):
    """Do not expose object state, location, or file-system details to the Worker."""


class DocumentParsingRepository:
    """Own document-parsing persistence without exposing ORM details to other modules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def submit_resume_parse_request(self, request: ResumeParseRequestV1) -> None:
        """Persist the fixed v1 parsing request in the caller's resource transaction."""
        matching_resume_id = await self._session.scalar(
            select(Resume.id).where(
                Resume.id == request.resume_id,
                Resume.candidate_id == request.candidate_id,
            )
        )
        if matching_resume_id is None:
            raise ValueError("resume parsing request does not match a candidate-owned resume")
        self._session.add(
            AsyncTaskRun(
                task_type="resume_parse",
                resource_type="resume",
                resource_id=request.resume_id,
                idempotency_key=f"resume_parse:{request.resume_id}:{request.task_version}",
                task_version=request.task_version,
                status="queued",
            )
        )

    async def get_profile(self, candidate_id: UUID, resume_id: UUID) -> CandidateProfile | None:
        statement = (
            select(CandidateProfile)
            .join(Resume, CandidateProfile.resume_id == Resume.id)
            .where(
                Resume.id == resume_id,
                Resume.candidate_id == candidate_id,
                Resume.parse_status == "succeeded",
            )
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def read_resume_for_processing(
        self, resume_id: UUID, storage_key_reader: Callable[[str], bytes]
    ) -> bytes:
        """Read only the ready object bound to a processing resume through a controlled port."""
        statement = (
            select(Resume, StoredFileObject)
            .join(StoredFileObject, Resume.stored_file_object_id == StoredFileObject.id)
            .where(
                Resume.id == resume_id,
                Resume.parse_status == "processing",
                StoredFileObject.status == "ready",
            )
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            raise ResumeStorageUnavailableError
        _, file_object = row
        try:
            return storage_key_reader(file_object.storage_key)
        except (OSError, ValueError) as exc:
            raise ResumeStorageUnavailableError from exc

    async def complete_resume_for_execution(
        self,
        *,
        task_run_id: UUID,
        resume_id: UUID,
        execution_token: UUID,
        profile: ResumeProfileExtractionV1,
    ) -> bool:
        """Atomically persist a validated profile and the matching worker terminal state."""
        async with self._session.begin():
            task = await self._locked_running_resume_task(task_run_id, resume_id, execution_token)
            if task is None:
                return False
            resume = await self._session.get(Resume, resume_id, with_for_update=True)
            if resume is None or resume.parse_status != "processing":
                return False
            existing_profile = await self._session.scalar(
                select(CandidateProfile)
                .where(CandidateProfile.resume_id == resume_id)
                .with_for_update()
            )
            if existing_profile is not None:
                return False
            self._session.add(
                CandidateProfile(
                    resume_id=resume.id,
                    full_name=profile.full_name,
                    phone=profile.phone,
                    email=profile.email,
                    matching_readiness=matching_readiness(profile),
                    target_job_titles=profile.target_job_titles,
                    skills=[item.model_dump(mode="json") for item in profile.skills],
                    work_experience_summary=[
                        item.model_dump(mode="json") for item in profile.work_experience_summary
                    ],
                    project_experience_summary=[
                        item.model_dump(mode="json") for item in profile.project_experience_summary
                    ],
                    years_of_experience=profile.years_of_experience,
                    education=profile.education,
                    expected_location=profile.expected_location,
                    expected_salary=profile.expected_salary,
                )
            )
            resume.parse_status = "succeeded"
            resume.failure_code = None
            task.status = "succeeded"
            task.failure_code = None
            task.finished_at = datetime.now(UTC)
            task.execution_token = None
            task.execution_lease_expires_at = None
        return True

    async def fail_resume_for_execution(
        self,
        *,
        task_run_id: UUID,
        resume_id: UUID,
        execution_token: UUID,
        failure_code: ParseFailureCode,
    ) -> bool:
        """Atomically persist a classified failure for the matching execution lease only."""
        async with self._session.begin():
            task = await self._locked_running_resume_task(task_run_id, resume_id, execution_token)
            if task is None:
                return False
            resume = await self._session.get(Resume, resume_id, with_for_update=True)
            if resume is None or resume.parse_status != "processing":
                return False
            resume.parse_status = "failed"
            resume.failure_code = failure_code
            task.status = "failed"
            task.failure_code = failure_code
            task.finished_at = datetime.now(UTC)
            task.execution_token = None
            task.execution_lease_expires_at = None
        return True

    async def _locked_running_resume_task(
        self, task_run_id: UUID, resume_id: UUID, execution_token: UUID
    ) -> AsyncTaskRun | None:
        statement = (
            select(AsyncTaskRun)
            .where(
                AsyncTaskRun.id == task_run_id,
                AsyncTaskRun.task_type == "resume_parse",
                AsyncTaskRun.resource_type == "resume",
                AsyncTaskRun.resource_id == resume_id,
                AsyncTaskRun.status == "running",
                AsyncTaskRun.execution_token == execution_token,
            )
            .with_for_update()
        )
        return await self._session.scalar(statement)
