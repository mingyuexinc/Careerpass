"""Validated contracts for deterministic S-03 JD extraction."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TextField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    normalized: str | None = None
    source_heading: str = Field(min_length=1)
    source_order: int = Field(ge=0)


class SalaryField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    min: float | None = Field(default=None, ge=0)
    max: float | None = Field(default=None, ge=0)
    currency: str | None = None
    period: str | None = None
    source_heading: str = Field(min_length=1)
    source_order: int = Field(ge=0)


class SectionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str = Field(min_length=1)
    normalized: str | None = None
    source_order: int = Field(ge=0)


class SectionField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    items: list[SectionItem]
    source_heading: str = Field(min_length=1)
    source_order: int = Field(ge=0)


class ExtraField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    normalized: str | None = None
    items: list[SectionItem] | None = None
    source_heading: str = Field(min_length=1)
    source_order: int = Field(ge=0)


class ParsedJobDescriptionFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TextField
    location: TextField
    salary_range: SalaryField
    responsibilities: SectionField
    requirements: SectionField
    company_name: TextField | None = None
    job_nature: TextField | None = None
    employment_type: TextField | None = None
    interview_mode: TextField | None = None
    summary: TextField | None = None
    additional_fields: dict[str, ExtraField] = Field(default_factory=dict)


class JobDescriptionParseSubmitRequest(BaseModel):
    local_path: str = Field(min_length=1, max_length=4096)


TaskStatus = Literal["queued", "running", "succeeded", "failed"]
ParseStatus = Literal["queued", "running", "succeeded", "failed"]
MatchingStatus = Literal["matching_ready", "matching_not_ready"]


class JobDescriptionParseSubmitData(BaseModel):
    task_id: UUID
    status: TaskStatus


class JobDescriptionParseRetryData(BaseModel):
    job_id: UUID
    task_id: UUID
    status: TaskStatus


class JobDescriptionParseResult(BaseModel):
    task_id: UUID
    job_id: UUID
    status: TaskStatus
    parse_status: ParseStatus
    matching_status: MatchingStatus | None = None
    snapshot_id: UUID | None = None
    schema_version: str | None = None
    fields: ParsedJobDescriptionFields | None = None
    failure_semantics: str | None = None
    failure_reason: str | None = None
    missing_core_fields: list[str] = Field(default_factory=list)
