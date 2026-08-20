"""Structured Qwen output for S10-01 resume answers."""

from pydantic import BaseModel, ConfigDict, Field


class ResumeAnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: bool
    answer: str = Field(min_length=1, max_length=2000)
    fact_refs: list[str] = Field(default_factory=list, max_length=12)
