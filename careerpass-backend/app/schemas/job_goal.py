"""Public S-06 job-goal request and response contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

JobGoalStatus = Literal["active", "achieved", "abandoned"]


class JobGoalInput(BaseModel):
    """Validated goal fields accepted by the current-goal save endpoint."""

    model_config = ConfigDict(extra="forbid")

    offer_target: StrictInt = Field(ge=1, le=10)
    title: str = Field(min_length=1, max_length=256)
    filters: str = Field(default="", max_length=20_000)

    @field_validator("title", "filters")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        if not value:
            raise ValueError("title is required")
        return value


class JobGoalResponse(BaseModel):
    """Safe current-goal projection exposed to the frontend and S-07."""

    id: UUID
    offer_target: int
    title: str
    filters: str
    status: JobGoalStatus
    created_at: datetime
    updated_at: datetime


class CurrentJobGoalResponse(BaseModel):
    goal: JobGoalResponse | None
