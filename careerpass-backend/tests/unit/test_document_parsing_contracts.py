"""Tests for the explicit candidate-preparation to document-parsing boundary."""

import asyncio
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.document_parsing import (
    ResumeParseRequestV1,
    ResumeProfileExtractionV1,
    WorkExperience,
    derive_years_of_experience,
    matching_readiness,
)
from app.services.document_parsing_service import DocumentParsingService


def test_resume_parse_request_is_fixed_to_the_v1_contract() -> None:
    request = ResumeParseRequestV1(candidate_id=uuid4(), resume_id=uuid4())

    assert request.task_version == "v1"


def test_resume_parse_request_rejects_unknown_contract_fields() -> None:
    with pytest.raises(ValidationError):
        ResumeParseRequestV1(candidate_id=uuid4(), resume_id=uuid4(), worker_path="untrusted")


def test_resume_profile_optional_fields_can_be_absent_without_parse_failure() -> None:
    profile = ResumeProfileExtractionV1(
        full_name="候选人",
        email="candidate@example.com",
        education="本科",
        project_experience_summary=[{"name": "项目一"}],
    )

    assert profile.target_job_titles == []
    assert profile.skills == []
    assert matching_readiness(profile) == "matching_ready"


def test_resume_profile_rejects_a_completely_empty_extraction() -> None:
    with pytest.raises(ValidationError):
        ResumeProfileExtractionV1()


def test_resume_profile_rejects_schema_field_name_as_education() -> None:
    with pytest.raises(ValidationError):
        ResumeProfileExtractionV1(full_name="候选人", education="full_name")


@pytest.mark.parametrize(
    ("experiences", "expected"),
    [
        ([], "unknown"),
        ([WorkExperience(company_name="无日期公司")], "unknown"),
        (
            [
                WorkExperience(
                    experience_type="internship",
                    start_date="2023-01",
                    end_date="2024-12",
                )
            ],
            "unknown",
        ),
        ([WorkExperience(start_date="2024-01", end_date="2024-05")], "5个月"),
        ([WorkExperience(start_date="2023-01", end_date="2024-05")], "1年"),
        ([WorkExperience(start_date="2023-01", end_date="2024-06")], "2年"),
        ([WorkExperience(start_date="2025-08", end_date="present")], "6个月"),
    ],
)
def test_years_of_experience_uses_confirmed_business_rounding(
    experiences: list[WorkExperience], expected: str
) -> None:
    assert derive_years_of_experience(experiences, parsed_on=date(2026, 1, 15)) == expected


def test_years_of_experience_merges_overlapping_work_periods_and_excludes_internships() -> None:
    experiences = [
        WorkExperience(start_date="2023-01", end_date="2023-12"),
        WorkExperience(start_date="2023-06", end_date="2024-06"),
        WorkExperience(
            experience_type="internship", start_date="2022-01", end_date="2022-12"
        ),
    ]

    assert derive_years_of_experience(experiences, parsed_on=date(2026, 1, 15)) == "2年"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2025年8月", "2025-08"),
        ("2025/08", "2025-08"),
        ("2025.8", "2025-08"),
        ("至今", "present"),
    ],
)
def test_work_experience_normalizes_explicit_month_formats(raw: str, expected: str) -> None:
    assert WorkExperience(start_date=raw).start_date == expected


@pytest.mark.parametrize(
    "profile",
    [
        ResumeProfileExtractionV1(email="candidate@example.com"),
        ResumeProfileExtractionV1(full_name="候选人", education="本科"),
        ResumeProfileExtractionV1(
            full_name="候选人",
            phone="13800000000",
            education="本科",
            project_experience_summary=[],
        ),
        ResumeProfileExtractionV1(
            full_name="候选人",
            phone="13800000000",
            education="本科",
            work_experience_summary=[{}],
        ),
    ],
)
def test_missing_minimum_business_fields_keeps_parse_success_but_not_ready(
    profile: ResumeProfileExtractionV1,
) -> None:
    assert matching_readiness(profile) == "matching_not_ready"


def test_document_parsing_service_returns_only_a_profile_owned_by_the_candidate() -> None:
    candidate_id = uuid4()
    resume_id = uuid4()

    class RecordingRepository:
        received: tuple[object, object] | None = None

        async def get_profile(self, received_candidate_id: object, received_resume_id: object):
            self.received = (received_candidate_id, received_resume_id)
            return type(
                "Profile",
                (),
                {
                    "id": uuid4(),
                    "resume_id": resume_id,
                    "target_job_titles": ["Backend Engineer"],
                    "skills": [],
                    "work_experience_summary": [],
                    "project_experience_summary": [],
                    "years_of_experience": "unknown",
                    "education": None,
                    "expected_location": None,
                    "expected_salary": None,
                },
            )()

    repository = RecordingRepository()
    result = asyncio.run(
        DocumentParsingService(repository=repository).get_profile(candidate_id, resume_id)  # type: ignore[arg-type]
    )

    assert repository.received == (candidate_id, resume_id)
    assert result is not None
    assert result.resume_id == resume_id
