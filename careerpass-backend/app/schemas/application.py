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


class ApplicationListResponse(BaseModel):
    run: dict[str, object] | None
    applications: list[ApplicationItem]
    total: int


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
