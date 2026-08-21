from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ResourceType = Literal["resume", "candidate_document", "job"]


class ResourceDeletionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: ResourceType
    resource_id: UUID
    deleted: bool
