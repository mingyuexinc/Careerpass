"""Versioned public contracts owned by the document-parsing module."""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ParseFailureCode = Literal[
    "unsupported_file",
    "file_unreadable",
    "storage_unavailable",
    "parser_timeout",
    "schema_validation_failed",
    "internal_error",
]
_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ResumeParseRequestV1(BaseModel):
    """Validated hand-off from candidate preparation to document parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    candidate_id: UUID
    resume_id: UUID
    task_version: Literal["v1"] = "v1"


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    proficiency: Literal["beginner", "intermediate", "advanced", "expert"] | None = None


class WorkExperience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_name: str | None = Field(default=None, max_length=128)
    title: str | None = Field(default=None, max_length=128)
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = Field(default=None, max_length=2000)
    highlights: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_month(cls, value: str | None) -> str | None:
        if value is not None and not _MONTH_PATTERN.fullmatch(value):
            raise ValueError("date must use YYYY-MM")
        return value


class ProjectExperience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    role: str | None = Field(default=None, max_length=128)
    summary: str | None = Field(default=None, max_length=2000)
    technologies: list[str] = Field(default_factory=list, max_length=30)
    highlights: list[str] = Field(default_factory=list, max_length=20)


class ResumeProfileExtractionV1(BaseModel):
    """Strict in-memory LLM contract; only validated instances may be persisted."""

    model_config = ConfigDict(extra="forbid")
    target_job_titles: list[str] = Field(min_length=1, max_length=10)
    skills: list[Skill] = Field(default_factory=list)
    work_experience_summary: list[WorkExperience] = Field(default_factory=list)
    project_experience_summary: list[ProjectExperience] = Field(default_factory=list)
    years_of_experience: int | None = Field(default=None, ge=0)
    education: str | None = Field(default=None, max_length=64)
    expected_location: str | None = Field(default=None, max_length=128)
    expected_salary: str | None = Field(default=None, max_length=64)

    @field_validator("target_job_titles")
    @classmethod
    def validate_titles(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(title.strip() for title in value if title.strip()))
        if not normalized or any(len(title) > 128 for title in normalized):
            raise ValueError("target_job_titles must contain non-empty values up to 128 chars")
        return normalized


class CandidateProfileResponse(ResumeProfileExtractionV1):
    profile_id: UUID
    resume_id: UUID
