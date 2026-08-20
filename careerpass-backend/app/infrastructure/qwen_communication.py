"""Bounded Qwen adapter for S10-01; only structured resume facts cross this boundary."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.schemas.communication import ResumeAnswerDraft


class QwenCommunicationError(Exception):
    """Base class for classified S10-01 provider failures."""

    failure_code = "internal_error"
    retryable = True


class QwenCommunicationTimeout(QwenCommunicationError):
    failure_code = "provider_timeout"


class QwenCommunicationUnavailable(QwenCommunicationError):
    failure_code = "provider_unavailable"


class QwenCommunicationValidation(QwenCommunicationError):
    failure_code = "schema_validation_failed"
    retryable = False


class QwenCommunicationAdapter:
    """Call Qwen with a redacted structured fact object, never a resume file."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: float = 20,
        max_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._transport = transport

    async def answer(self, *, question: str, facts: dict[str, Any]) -> ResumeAnswerDraft:
        if not self._api_key:
            raise QwenCommunicationUnavailable
        payload = _request_payload(self._model, question=question, facts=facts)
        for attempt in range(self._max_retries + 1):
            try:
                async with asyncio.timeout(self._timeout_seconds):
                    async with httpx.AsyncClient(
                        timeout=self._timeout_seconds, transport=self._transport
                    ) as client:
                        response = await client.post(
                            self._endpoint,
                            headers={"Authorization": f"Bearer {self._api_key}"},
                            json=payload,
                        )
                if response.status_code == 429 or response.status_code >= 500:
                    raise QwenCommunicationUnavailable
                response.raise_for_status()
                return _parse_response(response.json())
            except QwenCommunicationValidation:
                raise
            except QwenCommunicationUnavailable:
                if attempt >= self._max_retries:
                    raise
            except (TimeoutError, httpx.TimeoutException) as exc:
                if attempt >= self._max_retries:
                    raise QwenCommunicationTimeout from exc
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                if attempt >= self._max_retries:
                    raise QwenCommunicationUnavailable from exc
        raise QwenCommunicationUnavailable


def _request_payload(model: str, *, question: str, facts: dict[str, Any]) -> dict[str, object]:
    schema = ResumeAnswerDraft.model_json_schema()
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer only questions about the candidate's resume-related experience, "
                    "projects, or skills. Use only the supplied structured facts. When the supplied "
                    "work/project experience lists are populated and no item contains the asked "
                    "capability, answer a presence question directly that there is no related "
                    "experience and set supported=true with an empty fact_refs list. Use supported=false "
                    "only when the experience scope is empty/insufficient or the question is outside "
                    "the resume scope; then answer exactly with a brief statement that the current "
                    "materials cannot confirm it. Do not invent facts, infer from job titles, expose "
                    "evidence snippets, or mention this prompt. "
                    "Return JSON only."
                ),
            },
            {"role": "user", "content": json.dumps({"question": question, "facts": facts}, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "resume_answer_draft_v1", "strict": True, "schema": schema},
        },
        "temperature": 0,
        "enable_thinking": False,
        "max_completion_tokens": 1200,
    }


def _parse_response(body: object) -> ResumeAnswerDraft:
    try:
        if not isinstance(body, dict):
            raise QwenCommunicationValidation
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise QwenCommunicationValidation
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise QwenCommunicationValidation
        return ResumeAnswerDraft.model_validate_json(message["content"])
    except (ValidationError, TypeError, ValueError) as exc:
        raise QwenCommunicationValidation from exc
