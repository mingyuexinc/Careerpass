"""Application service for S-09 HR Application progress management."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.repositories.application_repository import (
    ApplicationRepository,
    to_hr_item,
)
from app.schemas.application import ApplicationStatus, HrApplicationItem


class HrApplicationNotFoundError(Exception):
    """The Application is not visible to the current HR identity."""


class ApplicationStatusConflictError(Exception):
    """The requested Application status transition is not allowed."""


APPLICATION_STATUS_ORDER: tuple[ApplicationStatus, ...] = (
    "submitted",
    "screening",
    "written_test",
    "interview_1",
    "interview_2",
    "interview_3",
    "hr_interview",
    "offer",
)
TERMINAL_STATUSES = {"offer", "terminated"}


class ApplicationService:
    """Coordinate HR-scoped Application state changes and Offer side effects."""

    def __init__(self, *, repository: ApplicationRepository) -> None:
        self._repository = repository

    async def list_current_for_hr(self, *, hr_profile_id: UUID) -> list[HrApplicationItem]:
        async with self._repository.transaction():
            return await self._repository.list_current_for_hr(hr_profile_id=hr_profile_id)

    async def update_status(
        self,
        *,
        application_id: UUID,
        hr_profile_id: UUID,
        status: ApplicationStatus,
    ) -> HrApplicationItem:
        async with self._repository.transaction():
            record = await self._repository.get_for_hr_update(
                application_id=application_id,
                hr_profile_id=hr_profile_id,
            )
            if record is None:
                raise HrApplicationNotFoundError

            current = record.application.status
            if current == status:
                return to_hr_item(record)
            if not _is_valid_transition(current=current, next_status=status):
                raise ApplicationStatusConflictError

            now = datetime.now(UTC)
            record.application.status = status
            record.application.updated_at = now
            await self._repository.append_status_event(
                record=record,
                from_status=current,
                to_status=status,
                now=now,
            )
            if status == "offer":
                offer_count = await self._repository.count_offers(
                    run_id=record.run.id,
                    candidate_id=record.application.candidate_id,
                )
                await self._repository.finish_for_offer_target(
                    record=record,
                    offer_count=offer_count,
                    now=now,
                )
            return to_hr_item(record)


def _is_valid_transition(*, current: str, next_status: ApplicationStatus) -> bool:
    if current in TERMINAL_STATUSES:
        return False
    if next_status == "terminated":
        return True
    try:
        return APPLICATION_STATUS_ORDER.index(next_status) > APPLICATION_STATUS_ORDER.index(current)
    except ValueError:
        return False
