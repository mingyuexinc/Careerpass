"""Repository boundary for HR-owned Job projections."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    Application,
    AsyncTaskRun,
    Job,
    Match,
    ParsedJobDescriptionSnapshot,
)
from app.schemas.job import HrJobItem, JobParseFailureKind, JobParseStatus
from app.schemas.job_description import ParsedJobDescriptionFields


@dataclass(frozen=True)
class HrJobRecord:
    """Persisted Job rows and their validated optional downstream data."""

    job: Job
    snapshot: ParsedJobDescriptionSnapshot | None
    parse_status: JobParseStatus | None
    parse_failure_kind: JobParseFailureKind | None
    parse_failure_reason: str | None
    parse_missing_core_fields: list[str]
    parse_can_retry: bool
    matching_eligible: bool
    match_started: bool


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
            match_started = bool(
                await self._session.scalar(
                    select(
                        Match.id,
                    )
                    .where(Match.job_id == job.id)
                    .limit(1)
                )
            ) or bool(
                await self._session.scalar(
                    select(Application.id).where(Application.job_id == job.id).limit(1)
                )
            )
            records.append(
                HrJobRecord(
                    job=job,
                    snapshot=snapshot,
                    parse_status=task_status
                    if task_status in {"queued", "running", "succeeded", "failed"}
                    else None,
                    parse_failure_kind=_failure_kind(task),
                    parse_failure_reason=task.failure_reason if task is not None else None,
                    parse_missing_core_fields=(task.missing_core_fields or []) if task is not None else [],
                    parse_can_retry=bool(task is not None and task.status == "failed" and not match_started),
                    matching_eligible=bool(task is not None and task.status == "succeeded" and snapshot is not None),
                    match_started=match_started,
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
        parse_failure_kind=record.parse_failure_kind,
        parse_failure_reason=record.parse_failure_reason,
        parse_missing_core_fields=record.parse_missing_core_fields,
        parse_can_retry=record.parse_can_retry,
        matching_eligible=record.matching_eligible,
        match_started=record.match_started,
    )


def _failure_kind(task: AsyncTaskRun | None) -> JobParseFailureKind | None:
    if task is None or task.status != "failed":
        return None
    if task.failure_semantics in {"input_unavailable", "storage_unavailable"}:
        return "storage_unavailable"
    if task.failure_semantics == "input_invalid":
        return "invalid_content"
    if task.failure_semantics == "core_fields_missing":
        return "missing_core_fields"
    return "retry_exhausted"
