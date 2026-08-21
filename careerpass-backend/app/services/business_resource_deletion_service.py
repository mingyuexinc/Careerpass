from __future__ import annotations

from uuid import UUID

from app.repositories.business_resource_deletion_repository import (
    BusinessResourceDeletionRepository,
    ResourceDeletionResult,
)


class BusinessResourceDeletionService:
    """Application boundary for S-11 deletion commands."""

    def __init__(self, *, repository: BusinessResourceDeletionRepository) -> None:
        self._repository = repository

    async def delete_resume(
        self, *, candidate_id: UUID, resume_id: UUID, actor_user_id: UUID, actor_role: str
    ) -> ResourceDeletionResult:
        return await self._repository.delete_resume(
            candidate_id=candidate_id,
            resume_id=resume_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )

    async def delete_candidate_document(
        self,
        *,
        candidate_id: UUID,
        document_id: UUID,
        actor_user_id: UUID,
        actor_role: str,
    ) -> ResourceDeletionResult:
        return await self._repository.delete_candidate_document(
            candidate_id=candidate_id,
            document_id=document_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )

    async def delete_job(
        self, *, hr_profile_id: UUID, job_id: UUID, actor_user_id: UUID, actor_role: str
    ) -> ResourceDeletionResult:
        return await self._repository.delete_job(
            hr_profile_id=hr_profile_id,
            job_id=job_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
