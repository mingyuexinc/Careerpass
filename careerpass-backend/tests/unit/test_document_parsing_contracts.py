"""Tests for the explicit candidate-preparation to document-parsing boundary."""

import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.document_parsing import ResumeParseRequestV1
from app.services.document_parsing_service import DocumentParsingService


def test_resume_parse_request_is_fixed_to_the_v1_contract() -> None:
    request = ResumeParseRequestV1(candidate_id=uuid4(), resume_id=uuid4())

    assert request.task_version == "v1"


def test_resume_parse_request_rejects_unknown_contract_fields() -> None:
    with pytest.raises(ValidationError):
        ResumeParseRequestV1(candidate_id=uuid4(), resume_id=uuid4(), worker_path="untrusted")


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
                    "years_of_experience": None,
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
