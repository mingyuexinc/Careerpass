"""Versioned public contracts owned by the document-parsing module."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ParseFailureCode = Literal[
    "unsupported_file",
    "file_unreadable",
    "storage_unavailable",
    "parser_timeout",
    "schema_validation_failed",
    "internal_error",
]
MatchingReadiness = Literal["matching_ready", "matching_not_ready"]
_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_YEARS_OF_EXPERIENCE_PATTERN = re.compile(r"^(?:unknown|(?:0|[1-9]\d*)(?:个月|年))$")
_RESERVED_PROFILE_FIELD_NAMES = {
    "full_name",
    "phone",
    "email",
    "target_job_titles",
    "skills",
    "work_experience_summary",
    "project_experience_summary",
    "years_of_experience",
    "education",
    "expected_location",
    "expected_salary",
}


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
    experience_type: Literal["work", "internship"] = "work"
    company_name: str | None = Field(default=None, max_length=128)
    title: str | None = Field(default=None, max_length=128)
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = Field(default=None, max_length=2000)
    highlights: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def validate_month(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("date must be a string")
        normalized = value.strip().casefold()
        if normalized in {"present", "current", "至今", "现在"}:
            return "present"
        localized = re.fullmatch(r"(\d{4})\s*(?:年|[./-])\s*(\d{1,2})\s*月?", normalized)
        if localized:
            year, month = (int(part) for part in localized.groups())
            if 1 <= month <= 12:
                return f"{year:04d}-{month:02d}"
        if not _MONTH_PATTERN.fullmatch(normalized):
            raise ValueError("date must use YYYY-MM or present")
        return normalized


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
    full_name: str | None = Field(
        default=None, max_length=128, description="Candidate name explicitly shown in the resume"
    )
    phone: str | None = Field(
        default=None, max_length=64, description="Phone number explicitly shown in the resume"
    )
    email: str | None = Field(
        default=None, max_length=254, description="Email address explicitly shown in the resume"
    )
    target_job_titles: list[str] = Field(default_factory=list, max_length=10)
    skills: list[Skill] = Field(default_factory=list)
    work_experience_summary: list[WorkExperience] = Field(
        default_factory=list, description="Every explicit work or internship experience entry"
    )
    project_experience_summary: list[ProjectExperience] = Field(
        default_factory=list, description="Every explicit project experience entry"
    )
    years_of_experience: str = Field(
        default="unknown",
        pattern=_YEARS_OF_EXPERIENCE_PATTERN.pattern,
        description="Deterministically derived work duration: unknown, x个月, or x年",
    )
    education: str | None = Field(
        default=None,
        max_length=64,
        description="Concise explicit education history including school, degree, or major",
    )
    expected_location: str | None = Field(default=None, max_length=128)
    expected_salary: str | None = Field(default=None, max_length=64)

    @field_validator("target_job_titles")
    @classmethod
    def validate_titles(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(title.strip() for title in value if title.strip()))
        if any(len(title) > 128 for title in normalized):
            raise ValueError("target_job_titles must contain values up to 128 chars")
        return normalized

    @field_validator("education")
    @classmethod
    def reject_schema_field_name_as_education(cls, value: str | None) -> str | None:
        if value is not None and value.strip().casefold() in _RESERVED_PROFILE_FIELD_NAMES:
            raise ValueError("education must be a resume fact, not a schema field name")
        return value

    @model_validator(mode="after")
    def consolidate_explicit_skills(self) -> "ResumeProfileExtractionV1":
        """Expose project technology facts in the profile-level skill field."""
        skills = list(self.skills)
        existing = {skill.name.casefold().strip() for skill in skills}
        for project in self.project_experience_summary:
            for technology in project.technologies:
                normalized = technology.casefold().strip()
                if normalized and normalized not in existing:
                    skills.append(Skill(name=technology.strip()))
                    existing.add(normalized)
        if len(skills) != len(self.skills):
            self.skills = skills
        return self

    @model_validator(mode="after")
    def reject_completely_empty_extraction(self) -> "ResumeProfileExtractionV1":
        scalar_facts = (
            self.full_name,
            self.phone,
            self.email,
            self.education,
            self.expected_location,
            self.expected_salary,
        )
        has_scalar_fact = any((value or "").strip() for value in scalar_facts)
        has_work_fact = any(
            item.company_name or item.title or item.summary or item.highlights
            for item in self.work_experience_summary
        )
        if not (
            has_scalar_fact
            or self.target_job_titles
            or self.skills
            or has_work_fact
            or self.project_experience_summary
            or self.years_of_experience != "unknown"
        ):
            raise ValueError("resume extraction must contain at least one explicit fact")
        return self


def derive_years_of_experience(
    experiences: list[WorkExperience],
    *,
    parsed_on: date | None = None,
) -> str:
    """Derive non-overlapping work duration; internships never contribute."""
    reference_date = parsed_on or date.today()
    intervals: list[tuple[int, int]] = []
    for item in experiences:
        if item.experience_type != "work" or not item.start_date or not item.end_date:
            continue
        start = _month_index(item.start_date)
        end = (
            reference_date.year * 12 + reference_date.month - 1
            if item.end_date == "present"
            else _month_index(item.end_date)
        )
        if start is not None and end is not None and start <= end:
            intervals.append((start, end))
    if not intervals:
        return "unknown"

    intervals.sort()
    merged: list[list[int]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    total_months = sum(end - start + 1 for start, end in merged)
    if total_months < 12:
        return f"{total_months}个月"
    return f"{(total_months + 6) // 12}年"


def _month_index(value: str) -> int | None:
    if not _MONTH_PATTERN.fullmatch(value):
        return None
    year, month = (int(part) for part in value.split("-"))
    return year * 12 + month - 1


def matching_readiness(profile: ResumeProfileExtractionV1) -> MatchingReadiness:
    """Derive matching admission from validated resume facts only."""
    has_contact = bool((profile.phone or "").strip() or (profile.email or "").strip())
    has_valid_work = any(
        item.company_name or item.title or item.summary or item.highlights
        for item in profile.work_experience_summary
    )
    has_valid_project = any(item.name.strip() for item in profile.project_experience_summary)
    has_work_or_project = has_valid_work or has_valid_project
    if (
        (profile.full_name or "").strip()
        and has_contact
        and (profile.education or "").strip()
        and has_work_or_project
    ):
        return "matching_ready"
    return "matching_not_ready"


class CandidateProfileResponse(ResumeProfileExtractionV1):
    profile_id: UUID
    resume_id: UUID
    matching_readiness: MatchingReadiness
