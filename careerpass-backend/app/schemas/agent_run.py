"""Safe S-07 Agent startup status and command projections."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

AgentRunStatus = Literal["running", "finished"]
AgentRunState = Literal["not_started", "running", "finished"]


class AgentRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: AgentRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    finish_reason: Literal["offer_target_reached", "no_match"] | None = None


class AgentRunStatusResponse(BaseModel):
    state: AgentRunState
    can_start: bool
    run: AgentRunSummary | None = None


class AgentRunStartResponse(BaseModel):
    run: AgentRunSummary
