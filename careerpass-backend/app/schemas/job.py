"""HR-facing Job query projections."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JobParseStatus = Literal["queued", "running", "succeeded", "failed"]
JobParseFailureKind = Literal[
    "storage_unavailable",
    "invalid_content",
    "missing_core_fields",
    "retry_exhausted",
]


class HrJobItem(BaseModel):
    """Minimal persisted Job projection for the HR workspace."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    file_name: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    created_at: datetime
    parse_status: JobParseStatus | None = None
    parse_failure_kind: JobParseFailureKind | None = None
    parse_failure_reason: str | None = None
    parse_missing_core_fields: list[str] = Field(default_factory=list)
    parse_can_retry: bool = False
    matching_eligible: bool = False
    match_started: bool = False


class HrJobListResponse(BaseModel):
    """Current active Jobs owned by the authenticated HR identity."""

    jobs: list[HrJobItem]
    total: int
