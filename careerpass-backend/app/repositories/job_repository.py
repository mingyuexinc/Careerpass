"""Repository boundary for HR-owned Job projections."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AsyncTaskRun,
    Job,
    ParsedJobDescriptionSnapshot,
)
from app.schemas.job import HrJobItem, JobParseStatus
from app.schemas.job_description import ParsedJobDescriptionFields


@dataclass(frozen=True)
class HrJobRecord:
    """Persisted Job rows and their validated optional downstream data."""

    job: Job
    snapshot: ParsedJobDescriptionSnapshot | None
    parse_status: JobParseStatus | None


class JobRepository:
    """Own HR Job ownership filtering and safe projection assembly."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_current_for_hr(self, *, hr_profile_id: UUID) -> list[HrJobItem]:
        rows = (
            await self._session.execute(
                select(Job, ParsedJobDescriptionSnapshot)
                .outerjoin(
                    ParsedJobDescriptionSnapshot,
                    ParsedJobDescriptionSnapshot.job_id == Job.id,
                )
                .where(
                    Job.hr_profile_id == hr_profile_id,
                    Job.deleted_at.is_(None),
                )
                .order_by(Job.created_at, Job.id)
            )
        ).all()

        records: list[HrJobRecord] = []
        for job, snapshot in rows:
            task = await self._session.scalar(
                select(AsyncTaskRun)
                .where(
                    AsyncTaskRun.resource_type == "job",
                    AsyncTaskRun.resource_id == job.id,
                    AsyncTaskRun.task_type == "job_jd_parse",
                )
                .order_by(desc(AsyncTaskRun.created_at), desc(AsyncTaskRun.id))
                .limit(1)
            )
            task_status = task.status if task is not None else None
            records.append(
                HrJobRecord(
                    job=job,
                    snapshot=snapshot,
                    parse_status=task_status
                    if task_status in {"queued", "running", "succeeded", "failed"}
                    else None,
                )
            )
        return [to_hr_item(record) for record in records]


def to_hr_item(record: HrJobRecord) -> HrJobItem:
    title: str | None = None
    company: str | None = None
    if record.snapshot is not None:
        try:
            fields = ParsedJobDescriptionFields.model_validate(record.snapshot.fields)
        except ValidationError:
            fields = None
        if fields is not None:
            title = fields.title.normalized or fields.title.raw
            if fields.company_name is not None:
                company = fields.company_name.normalized or fields.company_name.raw
    return HrJobItem(
        id=record.job.id,
        file_name=record.job.file_name,
        job_title=title,
        company_name=company,
        created_at=record.job.created_at,
        parse_status=record.parse_status,
    )
