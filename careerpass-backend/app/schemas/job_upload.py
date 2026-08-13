"""Public contracts for the S-02 batch Job upload endpoint."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

JobUploadOutcome = Literal["created", "duplicate", "failed"]
JobTaskStatus = Literal["queued", "existing"]


class JobUploadResult(BaseModel):
    index: int
    outcome: JobUploadOutcome
    job_id: UUID | None = None
    task_status: JobTaskStatus | None = None
    error_code: str | None = None


class JobUploadResponse(BaseModel):
    results: list[JobUploadResult]
