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
)


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
                    "years_of_experience": 3,
                }
            )
        )

    profile = asyncio.run(_adapter(handler).extract_profile("## Target role\nBackend Engineer"))

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
    assert body["enable_thinking"] is False
    assert body["temperature"] == 0


@pytest.mark.parametrize(
    "content",
    ["not-json", json.dumps({"target_job_titles": []}), json.dumps({"unexpected": True})],
)
def test_adapter_rejects_malformed_or_business_invalid_output(content: str) -> None:
    with pytest.raises(QwenProfileValidationError):
        asyncio.run(_adapter(lambda request: _response(content)).extract_profile("Target role: Engineer"))


def test_adapter_rejects_empty_markdown_without_provider_call() -> None:
    with pytest.raises(QwenProfileValidationError):
        asyncio.run(_adapter(lambda request: _response("{}")).extract_profile("   "))


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
