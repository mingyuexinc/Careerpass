"""Candidate-safe S-08 Application query projection."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ApplicationStatus = Literal[
    "submitted", "screening", "written_test", "interview_1", "interview_2",
    "interview_3", "hr_interview", "offer", "terminated",
]


class ApplicationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    job_id: UUID
    candidate_id: UUID
    status: ApplicationStatus
    job_title: str
    company_name: str | None = None
    location: str
    salary: str
    match_score: int
    recommendation_reason: str
    applied_at: datetime


class MatchingRoundSummary(BaseModel):
    """Safe counts explaining which Job inputs entered the current round."""

    model_config = ConfigDict(extra="forbid")

    active_job_count: int = 0
    eligible_job_count: int = 0
    pending_job_count: int = 0
    failed_job_count: int = 0
    evaluated_job_count: int = 0
    filtered_out_job_count: int = 0
    matched_job_count: int = 0


class ApplicationListResponse(BaseModel):
    run: dict[str, object] | None
    applications: list[ApplicationItem]
    total: int
    matching: MatchingRoundSummary


class HrApplicationItem(BaseModel):
    """Minimal HR-facing Application projection."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    job_id: UUID
    job_title: str
    company_name: str | None = None
    candidate_name: str
    status: ApplicationStatus


class HrApplicationListResponse(BaseModel):
    """Current HR-owned application projection."""

    applications: list[HrApplicationItem]
    total: int


class ApplicationStatusUpdateRequest(BaseModel):
    """Validated target status for one HR application update."""

    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus
