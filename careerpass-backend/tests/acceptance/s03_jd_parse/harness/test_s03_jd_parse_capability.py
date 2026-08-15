"""S-03 Capability Acceptance: fixed JD text to real parsed fields."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.parsers.job_description import parse_job_description

PROJECT_ROOT = Path(__file__).resolve().parents[5]
FIXTURE_ROOT = PROJECT_ROOT / "careerpass-backend" / "tests" / "fixtures" / "job_descriptions"
EXPECTED_PATH = Path(__file__).with_name("s03_acceptance_expected.json")


@pytest.mark.capability_acceptance
def test_s03_jd_parse_capability_acceptance() -> None:
    summary = _run_capability_acceptance()
    assert summary["passed"], (
        "S-03 Capability Acceptance failed; inspect Acceptance Artifact: "
        f"{summary['artifact_dir']}"
    )


def _run_capability_acceptance() -> dict[str, object]:
    started = time.monotonic()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    artifact_root = Path(
        os.environ.get(
            "S03_CAPABILITY_ARTIFACT_ROOT",
            str(
                PROJECT_ROOT
                / "careerpass-backend"
                / "tests"
                / "acceptance"
                / "s03_jd_parse"
                / "delivery-acceptance-results"
            ),
        )
    )
    artifact_dir = artifact_root / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []

    for fixture_name in manifest["fixtures"]:
        expected = manifest[fixture_name]
        record: dict[str, object] = {
            "fixture": fixture_name,
            "expected": expected,
            "checks": [],
            "outcome": "FAIL",
        }
        try:
            fixture_path = FIXTURE_ROOT / fixture_name
            content = fixture_path.read_bytes()
            fields, raw_sections = parse_job_description(content)
            actual_fields = fields.model_dump(mode="json")
            record["actual"] = {"parse_status": "succeeded", "fields": actual_fields}
            _assert_fields(record, actual_fields, raw_sections, content, expected)
            record["outcome"] = "PASS"
        except Exception as exc:
            record["error"] = _safe_error(exc)
        records.append(record)

    passed = len(records) == 2 and all(record["outcome"] == "PASS" for record in records)
    actual = {
        "scenario": "S-03 JD parse Capability Acceptance",
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "duration_ms": round((time.monotonic() - started) * 1000),
        "scope": "fixed JD text -> S-03 parser -> structured fields",
        "fixtures": records,
        "passed": passed,
    }
    (artifact_dir / "actual.json").write_text(
        json.dumps(actual, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (artifact_dir / "report.md").write_text(_render_report(actual), encoding="utf-8")
    return {"passed": passed, "artifact_dir": str(artifact_dir)}


def _assert_fields(
    record: dict[str, object],
    actual: dict[str, object],
    raw_sections: list[dict[str, object]],
    content: bytes,
    expected: dict[str, object],
) -> None:
    _check(record, "parse_status=succeeded", True, "succeeded")
    for field_name in ("title", "company_name", "location"):
        field = actual.get(field_name) or {}
        value = field.get("raw") if isinstance(field, dict) else None
        _check(record, f"{field_name} matches Expected", value == expected[field_name], value)

    salary = actual.get("salary_range") or {}
    _check(record, "salary minimum matches Expected", salary.get("min") == expected["salary_min"], salary.get("min"))
    _check(record, "salary maximum matches Expected", salary.get("max") == expected["salary_max"], salary.get("max"))
    _check(record, "salary period matches Expected", salary.get("period") == expected["salary_period"], salary.get("period"))

    source = content.decode("utf-8")
    for section_name, expected_count in (
        ("responsibilities", expected["responsibilities_count"]),
        ("requirements", expected["requirements_count"]),
    ):
        section = actual.get(section_name) or {}
        items = section.get("items", []) if isinstance(section, dict) else []
        _check(record, f"{section_name} item count", len(items) == expected_count, len(items))
        raw = section.get("raw") if isinstance(section, dict) else None
        heading = "岗位职责" if section_name == "responsibilities" else "任职要求"
        expected_raw = _fixture_section_raw(source, heading)
        _check(record, f"{section_name} raw comes from fixture", raw == expected_raw, raw)
        for item in items:
            item_raw = item.get("raw") if isinstance(item, dict) else ""
            _check(record, f"{section_name} item comes from fixture", bool(item_raw and item_raw in source), item_raw)

    additional = actual.get("additional_fields") or {}
    expected_keys = expected["additional_field_keys"]
    _check(record, "additional field keys preserved", sorted(additional) == sorted(expected_keys), sorted(additional))
    for heading in expected_keys:
        actual_extra = additional.get(heading) or {}
        expected_raw = _fixture_section_raw(source, heading)
        _check(record, f"additional field {heading} raw preserved", actual_extra.get("raw") == expected_raw, actual_extra.get("raw"))

    _check(record, "raw sections originate from fixture", bool(raw_sections), len(raw_sections))


def _check(record: dict[str, object], name: str, passed: bool, actual: object) -> None:
    checks = record.setdefault("checks", [])
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "actual": actual})
    if not passed:
        raise AssertionError(name)


def _fixture_section_raw(source: str, heading: str) -> str:
    heading_re = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
    current: str | None = None
    lines: list[str] = []
    for line in source.splitlines():
        match = heading_re.match(line)
        if match:
            if current == heading:
                return "\n".join(lines)
            current = match.group(1).strip()
            lines = []
        elif current == heading and line.strip():
            lines.append(line.strip())
    return "\n".join(lines) if current == heading else ""


def _safe_error(exc: Exception) -> str:
    return str(exc).replace("\r", " ").replace("\n", " ")[:240] or exc.__class__.__name__


def _render_report(actual: dict[str, object]) -> str:
    result = "PASS" if actual["passed"] else "FAIL"
    lines = [
        "# S-03 JD Parse Capability Acceptance Report",
        "",
        f"- Result: **{result}**",
        f"- Run ID: `{actual['run_id']}`",
        f"- Duration: `{actual['duration_ms']} ms`",
        "- Scope: fixed JD text → S-03 parser → structured fields",
        "- Fixtures: 001 and 002 under `tests/fixtures/job_descriptions/`",
        "",
    ]
    for record in actual["fixtures"]:
        lines.extend([f"## {record['fixture']}", "", f"Outcome: **{record['outcome']}**", ""])
        lines.extend(["| Assertion | Result | Actual |", "| --- | --- | --- |"])
        for check in record.get("checks", []):
            value = _report_value(check.get("actual"))
            lines.append(f"| {check['name']} | {check['status']} | `{value}` |")
        if record.get("error"):
            lines.extend(["", f"Failure: `{record['error']}`"])
        lines.append("")
    lines.append("完整机器可读实际结果见同目录 `actual.json`。")
    return "\n".join(lines) + "\n"


def _report_value(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return text.replace("`", "'").replace("\n", " ")[:180]
