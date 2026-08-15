"""Controlled DashScope Qwen adapter for deterministic resume profile extraction."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.parsers.resume_pdf import canonical_resume_text
from app.schemas.document_parsing import (
    ProjectExperience,
    ResumeProfileExtractionV1,
    WorkExperience,
    derive_years_of_experience,
)

logger = logging.getLogger(__name__)

_WORK_SECTION_MARKERS = (
    "工作经历",
    "工作经验",
    "实习经历",
    "职业经历",
    "employment history",
    "professional experience",
    "work experience",
)
_PROJECT_SECTION_MARKERS = (
    "代表项目",
    "项目经历",
    "项目经验",
    "project experience",
    "projects",
)
_EDUCATION_SECTION_MARKERS = (
    "教育背景",
    "教育经历",
    "education",
)
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d(?:[- ]?\d){8}(?!\d)")


class _ExperienceRecoveryV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_experience_summary: list[WorkExperience] = Field(default_factory=list)
    project_experience_summary: list[ProjectExperience] = Field(default_factory=list)


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
            async with asyncio.timeout(self._timeout_seconds):
                async with httpx.AsyncClient(
                    timeout=self._timeout_seconds, transport=self._transport
                ) as client:
                    canonical_source = canonical_resume_text(extracted_markdown)
                    has_canonical_source = canonical_source != extracted_markdown
                    recovery_profile = (
                        _deterministic_base_profile(canonical_source)
                        if has_canonical_source
                        else None
                    )
                    recovery_reasons: tuple[str, ...] = (
                        ("work_experience", "project_experience")
                        if has_canonical_source
                        else ()
                    )
                    for attempt in range(2):
                        recovering_experience = recovery_profile is not None
                        response = await client.post(
                            self._endpoint,
                            headers={"Authorization": f"Bearer {self._api_key}"},
                            json=(
                                _experience_recovery_payload(
                                    self._model,
                                    extracted_markdown,
                                    recovery_reasons,
                                )
                                if recovering_experience
                                else _request_payload(
                                    self._model,
                                    extracted_markdown,
                                    validation_retry=attempt > 0,
                                )
                            ),
                        )
                        if response.status_code == 429 or response.status_code >= 500:
                            raise QwenProfileUnavailableError
                        response.raise_for_status()
                        try:
                            if recovering_experience:
                                recovered = _validated_experience_recovery(
                                    response.json(), extracted_markdown
                                )
                                profile = recovery_profile.model_copy(
                                    update={
                                        **(
                                            {
                                                "work_experience_summary": (
                                                    recovered.work_experience_summary
                                                )
                                            }
                                            if _recovery_needs_work(recovery_reasons)
                                            else {}
                                        ),
                                        **(
                                            {
                                                "project_experience_summary": (
                                                    recovered.project_experience_summary
                                                )
                                            }
                                            if _recovery_needs_projects(recovery_reasons)
                                            else {}
                                        ),
                                    }
                                )
                            else:
                                profile = _validated_profile(response.json(), extracted_markdown)
                            invalid_facts = _invalid_explicit_source_facts(
                                extracted_markdown, profile
                            )
                            if invalid_facts:
                                logger.warning(
                                    "resume profile facts failed source validation: reasons=%s",
                                    ",".join(invalid_facts),
                                )
                                if attempt == 0 and _needs_experience_recovery(invalid_facts):
                                    recovery_profile = profile
                                    recovery_reasons = invalid_facts
                                    continue
                                raise QwenProfileValidationError
                            return profile.model_copy(
                                update={
                                    "years_of_experience": derive_years_of_experience(
                                        profile.work_experience_summary,
                                        parsed_on=date.today(),
                                    )
                                }
                            )
                        except QwenProfileValidationError:
                            if attempt == 1:
                                raise
            raise QwenProfileValidationError
        except QwenProfileError:
            raise
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise QwenProfileTimeoutError from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise QwenProfileUnavailableError from exc


def _request_payload(
    model: str,
    extracted_markdown: str,
    *,
    validation_retry: bool = False,
) -> dict[str, object]:
    retry_instruction = (
        "This is a validation retry because the previous response was structurally invalid, "
        "omitted an explicit fact, or returned a value unsupported by its source section. "
        "Re-scan every heading and associate each company, title, and date only with the same "
        "experience entry. Return all explicit contact, education, work, and project facts. "
        if validation_retry
        else ""
    )
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract only explicit facts from the supplied resume Markdown. "
                    "Return JSON only, matching ResumeProfileExtractionV1. "
                    "Extract full_name, phone, email, education, work experience, and project "
                    "experience wherever they are explicitly present. Preserve each work or "
                    "project entry as a separate structured item; do not collapse the entire "
                    "resume into one vague summary. Inspect the entire Markdown before answering, "
                    "including contact details near the header and education or project sections "
                    "that appear after work experience. Every JSON property is required in the "
                    "response; a required property may still use null or an empty array only when "
                    "that fact is genuinely absent. "
                    "target_job_titles must come only from an explicit target-role or job-intention "
                    "section; never infer, recommend, complete, or rewrite titles. "
                    "Use work for entries under a work or employment section and internship only "
                    "for entries under an explicit internship section. Never copy a company from "
                    "one entry into another. Scalar facts, company names, titles, and project names "
                    "must be supported by the supplied Markdown; never use JSON property names as "
                    "business values. Set years_of_experience to unknown because the application "
                    "derives it deterministically from validated non-internship date ranges. Use "
                    "present for the end_date of an explicitly current role. "
                    "Use null or empty arrays only when the corresponding fact is genuinely absent; "
                    "never return a completely empty profile for Markdown containing resume facts. "
                    f"{retry_instruction}"
                ),
            },
            {"role": "user", "content": f"Resume Markdown:\n{extracted_markdown}"},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "resume_profile_extraction_v1",
                "strict": True,
                "schema": _strict_profile_schema(),
            },
        },
        "temperature": 0,
        "enable_thinking": False,
        "max_completion_tokens": 5000,
    }


def _experience_recovery_payload(
    model: str,
    extracted_markdown: str,
    reasons: tuple[str, ...],
) -> dict[str, object]:
    work_instruction = (
        "Recover every work entry. "
        if _recovery_needs_work(reasons)
        else "Set work_experience_summary to an empty array; existing work is already valid. "
    )
    project_instruction = (
        "Recover every project entry. "
        if _recovery_needs_projects(reasons)
        else "Set project_experience_summary to an empty array; existing projects are valid. "
    )
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Recover only explicit work and project experience entries from the resume "
                    "Markdown. Return JSON only. Preserve every entry separately. Associate each "
                    "company, title, and date only with the same work entry; never copy a company "
                    "from another entry. Mark entries under an explicit internship section as "
                    "internship and all other employment entries as work. Use present only for an "
                    "explicitly current role. Company names, titles, and project names must be "
                    "copied exactly from the supplied Markdown. Never use a company from another "
                    "entry. All returned facts must be supported by the "
                    f"supplied Markdown. {work_instruction}{project_instruction}"
                ),
            },
            {"role": "user", "content": f"Resume Markdown:\n{extracted_markdown}"},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "resume_experience_recovery_v1",
                "strict": True,
                "schema": _strict_experience_recovery_schema(),
            },
        },
        "temperature": 0,
        "enable_thinking": False,
        "max_completion_tokens": 5000,
    }


def _invalid_explicit_source_facts(
    extracted_markdown: str,
    profile: ResumeProfileExtractionV1,
) -> tuple[str, ...]:
    grounding_source = canonical_resume_text(extracted_markdown)
    missing: list[str] = []
    if _has_section_heading(extracted_markdown, _WORK_SECTION_MARKERS) and not any(
        item.company_name or item.title or item.summary or item.highlights
        for item in profile.work_experience_summary
    ):
        missing.append("work_experience")
    if _has_section_heading(
        extracted_markdown, _PROJECT_SECTION_MARKERS
    ) and not profile.project_experience_summary:
        missing.append("project_experience")
    if _has_section_heading(extracted_markdown, _EDUCATION_SECTION_MARKERS) and not (
        profile.education or ""
    ).strip():
        missing.append("education")
    if _EMAIL_PATTERN.search(extracted_markdown) and not (profile.email or "").strip():
        missing.append("email")
    if _PHONE_PATTERN.search(extracted_markdown) and not (profile.phone or "").strip():
        missing.append("phone")
    for field_name in ("full_name", "phone", "email", "education"):
        value = getattr(profile, field_name)
        if value and not _source_supports_value(grounding_source, value):
            missing.append(f"unsupported_{field_name}")
    company_counts: dict[str, int] = {}
    for item in profile.work_experience_summary:
        for field_name in ("company_name", "title"):
            value = getattr(item, field_name)
            if value and not _source_supports_value(grounding_source, value):
                missing.append(f"unsupported_work_{field_name}")
        if item.company_name:
            key = _normalize_source_value(item.company_name)
            company_counts[key] = company_counts.get(key, 0) + 1
    normalized_source = _normalize_source_value(grounding_source)
    for company, extracted_count in company_counts.items():
        if company and normalized_source.count(company) < extracted_count:
            missing.append("unsupported_repeated_company")
    for item in profile.project_experience_summary:
        if not _source_supports_value(grounding_source, item.name):
            missing.append("unsupported_project_name")
    return tuple(missing)


def _needs_experience_recovery(reasons: tuple[str, ...]) -> bool:
    prefixes = (
        "work_experience",
        "project_experience",
        "unsupported_work_",
        "unsupported_repeated_company",
        "unsupported_project_name",
    )
    return any(reason.startswith(prefixes) for reason in reasons)


def _recovery_needs_work(reasons: tuple[str, ...]) -> bool:
    return any(
        reason == "work_experience"
        or reason.startswith("unsupported_work_")
        or reason == "unsupported_repeated_company"
        for reason in reasons
    )


def _recovery_needs_projects(reasons: tuple[str, ...]) -> bool:
    return any(
        reason == "project_experience" or reason == "unsupported_project_name"
        for reason in reasons
    )


def _source_supports_value(markdown: str, value: str) -> bool:
    normalized_source = _normalize_source_value(markdown)
    normalized_value = _normalize_source_value(value)
    if not normalized_value:
        return False
    if normalized_value in normalized_source:
        return True
    tokens = [
        _normalize_source_value(token)
        for token in re.split(r"[\s,，、/|;；()（）·]+", value)
        if len(_normalize_source_value(token)) >= 2
    ]
    return bool(tokens) and all(token in normalized_source for token in tokens)


def _normalize_source_value(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.casefold())


def _has_section_heading(markdown: str, markers: tuple[str, ...]) -> bool:
    for line in markdown.splitlines():
        normalized = re.sub(r"^[\s#>*|\-\d.、]+", "", line).strip().casefold()
        if any(normalized.startswith(marker.casefold()) for marker in markers):
            return True
    return False


def _strict_profile_schema() -> dict[str, object]:
    schema = ResumeProfileExtractionV1.model_json_schema()
    _require_all_object_properties(schema)
    return schema


def _strict_experience_recovery_schema() -> dict[str, object]:
    schema = _ExperienceRecoveryV1.model_json_schema()
    _require_all_object_properties(schema)
    return schema


def _require_all_object_properties(node: object) -> None:
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            node["required"] = list(properties)
        for value in node.values():
            _require_all_object_properties(value)
    elif isinstance(node, list):
        for value in node:
            _require_all_object_properties(value)


def _validated_profile(
    response_body: object,
    extracted_markdown: str,
) -> ResumeProfileExtractionV1:
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
        if isinstance(value, dict) and str(value.get("education", "")).casefold() in {
            field.casefold() for field in ResumeProfileExtractionV1.model_fields
        }:
            source_education = _education_from_explicit_section(extracted_markdown)
            if source_education:
                value["education"] = source_education
        return ResumeProfileExtractionV1.model_validate(value)
    except ValidationError as exc:
        diagnostics = [
            f"{'.'.join(str(part) for part in item['loc'])}:{item['type']}"
            for item in exc.errors(include_input=False, include_url=False)
        ]
        logger.warning(
            "resume profile schema validation failed: reasons=%s",
            ",".join(diagnostics),
        )
        raise QwenProfileValidationError from exc
    except json.JSONDecodeError as exc:
        logger.warning("resume profile schema validation failed: reasons=json_decode")
        raise QwenProfileValidationError from exc
    except TypeError as exc:
        logger.warning("resume profile schema validation failed: reasons=invalid_payload_type")
        raise QwenProfileValidationError from exc


def _validated_experience_recovery(
    response_body: object,
    extracted_markdown: str,
) -> _ExperienceRecoveryV1:
    if not isinstance(response_body, dict):
        raise QwenProfileValidationError
    choices = response_body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise QwenProfileValidationError
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise QwenProfileValidationError
    try:
        recovery = _ExperienceRecoveryV1.model_validate_json(message["content"])
    except ValidationError as exc:
        diagnostics = [
            f"{'.'.join(str(part) for part in item['loc'])}:{item['type']}"
            for item in exc.errors(include_input=False, include_url=False)
        ]
        logger.warning(
            "resume experience recovery validation failed: reasons=%s",
            ",".join(diagnostics),
        )
        raise QwenProfileValidationError from exc
    except (ValueError, TypeError) as exc:
        logger.warning("resume experience recovery validation failed: reasons=json_decode")
        raise QwenProfileValidationError from exc
    return recovery


def _education_from_explicit_section(markdown: str) -> str | None:
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        normalized = re.sub(r"^[\s#>*|\-\d.、]+", "", line).strip().casefold()
        if not any(normalized.startswith(marker.casefold()) for marker in _EDUCATION_SECTION_MARKERS):
            continue
        facts: list[str] = []
        for candidate in lines[index + 1 :]:
            if candidate.lstrip().startswith("#"):
                break
            cleaned = re.sub(r"^[\s>*|\-]+|[|]+$", "", candidate).strip()
            if not cleaned or re.fullmatch(r"[:\-\s|]+", cleaned):
                continue
            cleaned = _clean_education_line(cleaned)
            if cleaned:
                facts.append(cleaned)
            if len(facts) == 8:
                break
        if facts:
            records: list[str] = []
            current: list[str] = []
            for fact in facts:
                if re.search(r"(?:大学|学院|university|college)", fact, re.IGNORECASE):
                    if current:
                        records.append(" ".join(current))
                    current = [fact]
                else:
                    current.append(fact)
            if current:
                records.append(" ".join(current))
            result = ""
            for record in records or [" ".join(facts)]:
                candidate = f"{result}；{record}" if result else record
                if len(candidate) > 64:
                    break
                result = candidate
            return result or (records[0] if records else facts[0])[:64].rstrip()
    return None


def _clean_education_line(value: str) -> str:
    cleaned = re.sub(
        r"\d{4}\s*年\s*\d{1,2}\s*月\s*[-–—至]\s*\d{4}\s*年\s*\d{1,2}\s*月",
        " ",
        value,
    )
    cleaned = re.sub(r"\d{4}-\d{2}\s*[-–—至]\s*\d{4}-\d{2}", " ", cleaned)
    cleaned = re.sub(r"[（(]?\s*GPA\s*[:：][^）)]*[）)]?", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bfull[- ]?time\b|全日制", " ", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip(" ;；,，")


def _deterministic_base_profile(canonical_source: str) -> ResumeProfileExtractionV1:
    email_match = _EMAIL_PATTERN.search(canonical_source)
    phone_match = _PHONE_PATTERN.search(canonical_source)
    return ResumeProfileExtractionV1(
        full_name=_first_explicit_name(canonical_source),
        phone=phone_match.group(0) if phone_match else None,
        email=email_match.group(0) if email_match else None,
        education=_education_from_explicit_section(canonical_source),
    )


def _first_explicit_name(canonical_source: str) -> str | None:
    for line in canonical_source.splitlines()[:8]:
        candidate = re.sub(r"^[\s#>*|\-]+|[|]+$", "", line).strip()
        if re.fullmatch(r"[\u4e00-\u9fff·]{2,8}", candidate):
            return candidate
        if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,63}", candidate):
            return candidate
    return None
