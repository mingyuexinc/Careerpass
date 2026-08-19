"""Tests for Qwen profile extraction boundaries and failure classification."""

import asyncio
import json

import httpx
import pytest

from app.infrastructure.qwen_profile import (
    QwenProfileAdapter,
    QwenProfileTimeoutError,
    QwenProfileUnavailableError,
    QwenProfileValidationError,
    _education_from_explicit_section,
)
from app.parsers.resume_pdf import compose_resume_extraction_source


def _response(content: object, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json={"choices": [{"message": {"content": content}}]})


def _adapter(handler) -> QwenProfileAdapter:
    return QwenProfileAdapter(
        api_key="test-key",
        base_url="https://example.invalid/compatible-mode/v1",
        model="qwen-plus",
        transport=httpx.MockTransport(handler),
    )


def test_adapter_uses_json_mode_and_returns_only_validated_profile() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return _response(
            json.dumps(
                {
                    "target_job_titles": ["Backend Engineer"],
                    "skills": [{"name": "Python", "proficiency": "advanced"}],
                    "years_of_experience": "unknown",
                }
            )
        )

    profile = asyncio.run(_adapter(handler).extract_profile("## Target role\nBackend Engineer\nPython"))

    assert profile.target_job_titles == ["Backend Engineer"]
    assert profile.skills[0].name == "Python"
    assert captured["url"] == "https://example.invalid/compatible-mode/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    body = captured["body"]
    assert isinstance(body, dict)
    response_format = body["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "resume_profile_extraction_v1"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    assert set(schema["$defs"]["WorkExperience"]["required"]) == set(
        schema["$defs"]["WorkExperience"]["properties"]
    )
    assert body["enable_thinking"] is False
    assert body["temperature"] == 0
    assert body["max_completion_tokens"] == 5000


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        "{}",
        json.dumps({"work_experience_summary": [{"start_date": "2024"}]}),
        json.dumps({"unexpected": True}),
    ],
)
def test_adapter_rejects_malformed_or_schema_invalid_output(content: str) -> None:
    with pytest.raises(QwenProfileValidationError):
        asyncio.run(_adapter(lambda request: _response(content)).extract_profile("Target role: Engineer"))


def test_adapter_rejects_empty_markdown_without_provider_call() -> None:
    with pytest.raises(QwenProfileValidationError):
        asyncio.run(_adapter(lambda request: _response("{}")).extract_profile("   "))


def test_adapter_retries_one_schema_invalid_provider_response() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _response("{}")
        return _response(
            json.dumps(
                {
                    "full_name": "Candidate",
                    "phone": None,
                    "email": "candidate@example.com",
                    "target_job_titles": [],
                    "skills": [],
                    "work_experience_summary": [],
                    "project_experience_summary": [{"name": "Project"}],
                    "years_of_experience": "unknown",
                    "education": "Bachelor",
                    "expected_location": None,
                    "expected_salary": None,
                }
            )
        )

    profile = asyncio.run(
        _adapter(handler).extract_profile(
            "Candidate candidate@example.com Bachelor Project"
        )
    )

    assert calls == 2
    assert profile.full_name == "Candidate"


def test_adapter_retries_when_explicit_experience_section_was_omitted() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        if len(bodies) == 2:
            return _response(
                json.dumps(
                    {
                        "work_experience_summary": [],
                        "project_experience_summary": [{"name": "Explicit project"}],
                    }
                )
            )
        return _response(
            json.dumps(
                {
                    "full_name": "Candidate",
                    "phone": None,
                    "email": "candidate@example.com",
                    "target_job_titles": [],
                    "skills": [],
                    "work_experience_summary": [],
                    "project_experience_summary": [],
                    "years_of_experience": "unknown",
                    "education": "Bachelor",
                    "expected_location": None,
                    "expected_salary": None,
                }
            )
        )

    profile = asyncio.run(
        _adapter(handler).extract_profile(
            "Candidate candidate@example.com Bachelor\n# Projects\nExplicit project details"
        )
    )

    assert len(bodies) == 2
    assert profile.project_experience_summary[0].name == "Explicit project"
    retry_message = bodies[1]["messages"][0]["content"]
    assert "Recover only explicit skills, work, and project" in retry_message


def test_adapter_rejects_explicit_skill_section_when_recovery_still_omits_skills() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _response(
                json.dumps(
                    {
                        "full_name": "Candidate",
                        "phone": None,
                        "email": "candidate@example.com",
                        "target_job_titles": [],
                        "skills": [],
                        "work_experience_summary": [],
                        "project_experience_summary": [],
                        "years_of_experience": "unknown",
                        "education": "Bachelor",
                        "expected_location": None,
                        "expected_salary": None,
                    }
                )
            )
        return _response(
            json.dumps(
                {
                    "skills": [],
                    "work_experience_summary": [],
                    "project_experience_summary": [],
                }
            )
        )

    with pytest.raises(QwenProfileValidationError):
        asyncio.run(
            _adapter(handler).extract_profile(
                "Candidate candidate@example.com Bachelor\n# 专业技能\nPython"
            )
        )

    assert calls == 2


def test_adapter_rejects_repeated_omission_of_an_explicit_section() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response(
            json.dumps(
                {
                    "full_name": "Candidate",
                    "phone": "13800000000",
                    "email": None,
                    "target_job_titles": [],
                    "skills": [],
                    "work_experience_summary": [],
                    "project_experience_summary": [],
                    "years_of_experience": "unknown",
                    "education": "Bachelor",
                    "expected_location": None,
                    "expected_salary": None,
                }
            )
        )

    with pytest.raises(QwenProfileValidationError):
        asyncio.run(_adapter(handler).extract_profile("# 工作经历\nExplicit employment"))

    assert calls == 2


def test_adapter_retries_schema_name_leaked_into_education() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        education = "full_name" if calls == 1 else "Example University Bachelor"
        return _response(
            json.dumps(
                {
                    "full_name": "Candidate",
                    "phone": None,
                    "email": "candidate@example.com",
                    "target_job_titles": [],
                    "skills": [],
                    "work_experience_summary": [],
                    "project_experience_summary": [{"name": "Explicit Project"}],
                    "years_of_experience": "unknown",
                    "education": education,
                    "expected_location": None,
                    "expected_salary": None,
                }
            )
        )

    profile = asyncio.run(
        _adapter(handler).extract_profile(
            "Candidate candidate@example.com Example University Bachelor Explicit Project"
        )
    )

    assert calls == 2
    assert profile.education == "Example University Bachelor"


def test_adapter_repairs_schema_name_education_from_explicit_source_section() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response(
            json.dumps(
                {
                    "full_name": "Candidate",
                    "phone": None,
                    "email": "candidate@example.com",
                    "target_job_titles": [],
                    "skills": [],
                    "work_experience_summary": [],
                    "project_experience_summary": [{"name": "Explicit Project"}],
                    "years_of_experience": "unknown",
                    "education": "full_name",
                    "expected_location": None,
                    "expected_salary": None,
                }
            )
        )

    profile = asyncio.run(
        _adapter(handler).extract_profile(
            "Candidate candidate@example.com\n# Education\nExample University Bachelor\n"
            "# Projects\nExplicit Project"
        )
    )

    assert calls == 1
    assert profile.education == "Example University Bachelor"


def test_canonical_pdf_source_uses_deterministic_core_and_recovery_schema() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return _response(
            json.dumps(
                {
                    "skills": [{"name": "RAG", "proficiency": "advanced"}],
                    "work_experience_summary": [
                        {
                            "experience_type": "work",
                            "company_name": "Example Company",
                            "title": "Engineer",
                            "start_date": "2024-01",
                            "end_date": "present",
                            "summary": None,
                            "highlights": [],
                        }
                    ],
                    "project_experience_summary": [{"name": "Example Project"}],
                }
            )
        )

    canonical = (
        "候选人\ncandidate@example.com 13800000000\n# 工作经历\n"
        "Example Company Engineer 2024-01 present\n# 项目经历\nExample Project\n"
        "# 专业技能\nRAG\n# 教育经历\nExample University Bachelor"
    )
    profile = asyncio.run(
        _adapter(handler).extract_profile(compose_resume_extraction_source(canonical, ""))
    )

    assert captured["response_format"]["json_schema"]["name"] == "resume_experience_recovery_v1"
    assert profile.full_name == "候选人"
    assert profile.email == "candidate@example.com"
    assert profile.education == "Example University Bachelor"
    assert profile.work_experience_summary[0].company_name == "Example Company"
    assert profile.skills[0].name == "RAG"
    assert profile.years_of_experience != "unknown"


def test_education_summary_keeps_complete_records_without_dates_or_gpa() -> None:
    source = (
        "# 教育经历\n"
        "电子科技大学 2020年09月 - 2023年06月\n"
        "软件工程 硕士（GPA:3.85/5）全日制\n"
        "福州大学 2016年09月 - 2020年06月\n"
        "电子信息工程 本科 全日制\n"
        "# 个人优势\n"
    )

    assert _education_from_explicit_section(source) == (
        "电子科技大学 软件工程 硕士；福州大学 电子信息工程 本科"
    )


def test_adapter_retries_when_a_company_is_reused_without_source_support() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        second_company = "First Company" if calls == 1 else "Second Company"
        if calls == 2:
            return _response(
                json.dumps(
                    {
                        "work_experience_summary": [
                            {
                                "experience_type": "work",
                                "company_name": "First Company",
                                "title": "Engineer",
                                "start_date": "2023-01",
                                "end_date": "2024-05",
                                "summary": None,
                                "highlights": [],
                            },
                            {
                                "experience_type": "work",
                                "company_name": "Second Company",
                                "title": "Developer",
                                "start_date": "2024-06",
                                "end_date": "present",
                                "summary": None,
                                "highlights": [],
                            },
                        ],
                        "project_experience_summary": [],
                    }
                )
            )
        return _response(
            json.dumps(
                {
                    "full_name": "Candidate",
                    "phone": None,
                    "email": "candidate@example.com",
                    "target_job_titles": [],
                    "skills": [],
                    "work_experience_summary": [
                        {
                            "experience_type": "work",
                            "company_name": "First Company",
                            "title": "Engineer",
                            "start_date": "2023-01",
                            "end_date": "2024-05",
                            "summary": None,
                            "highlights": [],
                        },
                        {
                            "experience_type": "work",
                            "company_name": second_company,
                            "title": "Developer",
                            "start_date": "2024-06",
                            "end_date": "present",
                            "summary": None,
                            "highlights": [],
                        },
                    ],
                    "project_experience_summary": [],
                    "years_of_experience": "unknown",
                    "education": None,
                    "expected_location": None,
                    "expected_salary": None,
                }
            )
        )

    profile = asyncio.run(
        _adapter(handler).extract_profile(
            "Candidate candidate@example.com First Company Engineer 2023-01 2024-05 "
            "Second Company Developer 2024-06 至今"
        )
    )

    assert calls == 2
    assert profile.work_experience_summary[1].company_name == "Second Company"
    assert profile.years_of_experience != "unknown"


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (lambda request: _response("{}", 429), QwenProfileUnavailableError),
        (lambda request: _response("{}", 500), QwenProfileUnavailableError),
        (lambda request: _raise_timeout(), QwenProfileTimeoutError),
    ],
)
def test_adapter_classifies_provider_failures(handler, expected) -> None:
    with pytest.raises(expected):
        asyncio.run(_adapter(handler).extract_profile("Target role: Engineer"))


def _raise_timeout() -> httpx.Response:
    raise httpx.ReadTimeout("timeout")
