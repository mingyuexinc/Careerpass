"""Controlled DashScope Qwen adapter for deterministic resume profile extraction."""

from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from app.schemas.document_parsing import ResumeProfileExtractionV1


class QwenProfileError(Exception):
    """Base class for safe, classified Qwen profile failures."""

    failure_code: str
    retryable: bool


class QwenProfileTimeoutError(QwenProfileError):
    failure_code = "parser_timeout"
    retryable = True


class QwenProfileUnavailableError(QwenProfileError):
    failure_code = "internal_error"
    retryable = True


class QwenProfileValidationError(QwenProfileError):
    failure_code = "schema_validation_failed"
    retryable = False


class QwenProfileAdapter:
    """Call the OpenAI-compatible API and return only a validated profile fact model."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 25,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def extract_profile(self, extracted_markdown: str) -> ResumeProfileExtractionV1:
        """Extract only explicit resume facts; no raw provider response leaves this boundary."""
        if not extracted_markdown.strip():
            raise QwenProfileValidationError
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, transport=self._transport
            ) as client:
                response = await client.post(
                    self._endpoint,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=_request_payload(self._model, extracted_markdown),
                )
            if response.status_code == 429 or response.status_code >= 500:
                raise QwenProfileUnavailableError
            response.raise_for_status()
            return _validated_profile(response.json())
        except QwenProfileError:
            raise
        except httpx.TimeoutException as exc:
            raise QwenProfileTimeoutError from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise QwenProfileUnavailableError from exc


def _request_payload(model: str, extracted_markdown: str) -> dict[str, object]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract only explicit facts from the supplied resume Markdown. "
                    "Return JSON only, matching ResumeProfileExtractionV1. "
                    "target_job_titles must come only from an explicit target-role or job-intention "
                    "section; never infer, recommend, complete, or rewrite titles. "
                    "Use null or empty arrays when other facts are absent."
                ),
            },
            {"role": "user", "content": f"Resume Markdown:\n{extracted_markdown}"},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "resume_profile_extraction_v1",
                "strict": True,
                "schema": ResumeProfileExtractionV1.model_json_schema(),
            },
        },
        "temperature": 0,
        "enable_thinking": False,
        "max_completion_tokens": 1200,
    }


def _validated_profile(response_body: object) -> ResumeProfileExtractionV1:
    if not isinstance(response_body, dict):
        raise QwenProfileValidationError
    choices = response_body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise QwenProfileValidationError
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise QwenProfileValidationError
    try:
        value = json.loads(message["content"])
        return ResumeProfileExtractionV1.model_validate(value)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise QwenProfileValidationError from exc
