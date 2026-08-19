"""Application service for HR-owned Job projections."""

from __future__ import annotations

from uuid import UUID

from app.repositories.job_repository import JobRepository
from app.schemas.job import HrJobItem


class JobService:
    """Expose safe, current HR Job projections."""

    def __init__(self, *, repository: JobRepository) -> None:
        self._repository = repository

    async def list_current_for_hr(self, *, hr_profile_id: UUID) -> list[HrJobItem]:
        return await self._repository.list_current_for_hr(hr_profile_id=hr_profile_id)
