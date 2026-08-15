"""Capability Acceptance for the real S-04 resume parsing core."""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.infrastructure.mineru_mcp import MineruMcpAdapter
from app.infrastructure.mineru_mcp_client import MineruStdioClient
from app.infrastructure.qwen_profile import QwenProfileAdapter
from app.parsers.resume_pdf import compose_resume_extraction_source, extract_native_pdf_text
from app.schemas.document_parsing import ResumeProfileExtractionV1, matching_readiness

PROJECT_ROOT = Path(__file__).resolve().parents[5]
FIXTURE_PATH = PROJECT_ROOT / "careerpass-backend/tests/fixtures/candidate_preparation/resumes/resume_1.pdf"


@pytest.mark.capability_acceptance
def test_fixed_pdf_produces_a_valid_resume_profile() -> None:
    result = _run_acceptance()
    assert result["passed"], result["checks"]


def _run_acceptance() -> dict[str, object]:
    artifact_root = Path(
        os.getenv(
            "S04_CAPABILITY_ARTIFACT_ROOT",
            str(PROJECT_ROOT / "careerpass-backend/tests/acceptance/s04_resume_parse/delivery-acceptance-results"),
        )
    )
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    artifact_dir = artifact_root / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    checks: list[dict[str, object]] = []
    started = time.monotonic()
    profile: ResumeProfileExtractionV1 | None = None
    error: str | None = None
    try:
        if not FIXTURE_PATH.is_file():
            raise FileNotFoundError(f"fixed PDF fixture not found: {FIXTURE_PATH}")
        profile = asyncio.run(_parse_fixture(FIXTURE_PATH.read_bytes()))
    except Exception as exc:  # noqa: BLE001 - acceptance report needs a stable failure record
        failure_code = getattr(exc, "failure_code", None)
        error = f"{type(exc).__name__}:{failure_code or 'unclassified'}"

    checks.append(_check("fixed_pdf_exists", FIXTURE_PATH.is_file()))
    checks.append(_check("parse_succeeded", profile is not None))
    checks.append(_check("schema_valid", profile is not None))
    readiness = matching_readiness(profile) if profile is not None else "not_evaluated"
    checks.append(_check("matching_readiness_calculated", readiness in {"matching_ready", "matching_not_ready"}))
    checks.append(_check("full_name_present", bool(profile and (profile.full_name or "").strip())))
    checks.append(
        _check(
            "contact_present",
            bool(profile and ((profile.phone or "").strip() or (profile.email or "").strip())),
        )
    )
    checks.append(_check("education_present", bool(profile and (profile.education or "").strip())))
    checks.append(
        _check(
            "experience_duration_derived",
            bool(profile and profile.years_of_experience != "unknown"),
        )
    )
    work_companies = [
        item.company_name.strip()
        for item in (profile.work_experience_summary if profile else [])
        if item.experience_type == "work" and item.company_name
    ]
    checks.append(
        _check(
            "fixed_fixture_work_companies_distinct",
            len(work_companies) >= 2 and len(work_companies) == len(set(work_companies)),
        )
    )
    checks.append(
        _check(
            "work_or_project_present",
            bool(
                profile
                and (profile.work_experience_summary or profile.project_experience_summary)
            ),
        )
    )
    checks.append(_check("matching_ready", readiness == "matching_ready"))

    result: dict[str, object] = {
        "acceptance": "S-04 resume parse capability",
        "fixture": FIXTURE_PATH.name,
        "parse_status": "succeeded" if profile is not None else "failed",
        "matching_readiness": readiness,
        "duration_ms": round((time.monotonic() - started) * 1000, 1),
        "passed": all(bool(item["passed"]) for item in checks),
        "checks": checks,
        "error": error,
        "actual_profile": _safe_profile(profile) if profile is not None else None,
    }
    (artifact_dir / "actual.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (artifact_dir / "report.md").write_text(_render_report(result), encoding="utf-8")
    return result


async def _parse_fixture(pdf_bytes: bytes) -> ResumeProfileExtractionV1:
    mineru_token = os.getenv("MINERU_API_TOKEN") or os.getenv("MINERU_API_KEY")
    qwen_api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not qwen_api_key:
        raise RuntimeError("QWEN_API_KEY or DASHSCOPE_API_KEY is required")

    command = os.getenv("MINERU_MCP_COMMAND", "uvx")
    command_args = os.getenv("MINERU_MCP_ARGS", "mineru-open-mcp").split()
    timeout = float(os.getenv("S04_CAPABILITY_TIMEOUT_SECONDS", "120"))
    mineru_timeout = min(45.0, timeout * 0.4)
    qwen_timeout = max(10.0, timeout - 5.0)
    try:
        native_text = extract_native_pdf_text(pdf_bytes)
        extraction_source = compose_resume_extraction_source(native_text, "")
    except ValueError:
        if not mineru_token:
            raise RuntimeError("MINERU_API_TOKEN or MINERU_API_KEY is required for fallback")
        mineru_client = MineruStdioClient(
            command=command,
            command_args=tuple(command_args),
            api_token=mineru_token,
            timeout_seconds=mineru_timeout,
        )
        extraction_source = await MineruMcpAdapter(tool=mineru_client).extract_markdown(
            pdf_bytes
        )
    adapter = QwenProfileAdapter(
        api_key=qwen_api_key,
        base_url=os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        model=os.getenv("QWEN_PROFILE_MODEL", "qwen-plus"),
        timeout_seconds=qwen_timeout,
    )
    return await adapter.extract_profile(extraction_source)


def _check(name: str, passed: bool) -> dict[str, object]:
    return {"name": name, "passed": passed}


def _safe_profile(profile: ResumeProfileExtractionV1) -> dict[str, object]:
    payload = profile.model_dump(mode="json")
    for field in ("phone", "email"):
        if payload.get(field):
            payload[field] = "[REDACTED]"
    return payload


def _render_report(result: dict[str, object]) -> str:
    lines = [
        "# S-04 Resume Parse Capability Acceptance",
        "",
        f"- Fixture: `{result['fixture']}`",
        f"- Parse status: `{result['parse_status']}`",
        f"- Matching readiness: `{result['matching_readiness']}`",
        f"- Passed: `{result['passed']}`",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    for item in result["checks"]:  # type: ignore[union-attr]
        lines.append(f"| `{item['name']}` | `{item['passed']}` |")
    if result.get("error"):
        safe_error = str(result["error"]).replace("`", "'")[:180]
        lines.extend(["", "## Error", "", f"`{safe_error}`"])
    lines.extend(["", "## Structured profile", "", "联系方式已在验收产物中脱敏；不输出简历原文。"])
    return "\n".join(lines) + "\n"
