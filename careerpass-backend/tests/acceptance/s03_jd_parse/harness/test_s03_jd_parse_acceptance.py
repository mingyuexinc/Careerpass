"""S-03 internal capability acceptance through the real async task chain."""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from tests.acceptance.s03_jd_parse.harness.s03_acceptance_factory import (
    PreparedS03Fixture,
    S03AcceptanceFactory,
)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
API_BASE_URL = os.environ.get("S03_ACCEPTANCE_API_BASE_URL", "http://localhost:8080")
TERMINAL_STATUSES = {"succeeded", "failed"}


@pytest.mark.acceptance
def test_s03_jd_parse_acceptance() -> None:
    summary = asyncio.run(_run_acceptance())
    assert summary["passed"], (
        "S-03 acceptance failed; inspect Acceptance Artifact: "
        f"{summary['artifact_dir']}"
    )


async def _run_acceptance() -> dict[str, object]:
    started = time.monotonic()
    started_at = datetime.now(UTC).isoformat()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    artifact_dir = Path(
        os.environ.get(
            "S03_ACCEPTANCE_ARTIFACT_ROOT",
            str(
                PROJECT_ROOT
                / "careerpass-backend"
                / "tests"
                / "acceptance"
                / "s03_jd_parse"
                / "delivery-acceptance-results"
            ),
        )
    ) / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    failures: list[str] = []
    factory: S03AcceptanceFactory | None = None

    try:
        factory = S03AcceptanceFactory(PROJECT_ROOT)
        for fixture in factory.fixtures():
            record: dict[str, object] = {
                "fixture": fixture.name,
                "expected": fixture.expected,
                "task_statuses": [],
                "checks": [],
                "outcome": "FAIL",
            }
            prepared: PreparedS03Fixture | None = None
            try:
                prepared = await factory.prepare(fixture)
                record["resources"] = {
                    "job_id": str(prepared.created.job_id),
                    "file_object_id": str(prepared.created.file_object_id),
                }
                with httpx.Client(
                    base_url=API_BASE_URL,
                    headers={"Authorization": f"Bearer {prepared.token}"},
                    timeout=10.0,
                ) as client:
                    first = _submit(client, prepared.container_path)
                    record["task_statuses"] = [first["status"]]
                    _check(record, "submit status is queued", first["status"] == "queued", first)
                    task_id = first["task_id"]
                    result = _poll_result(client, task_id, record)
                    record["actual"] = result
                    _assert_parse_result(record, result, fixture.expected, prepared.content)

                    duplicate = _submit(client, prepared.container_path)
                    record["duplicate_submit"] = duplicate
                    _check(
                        record,
                        "duplicate submission reuses task",
                        duplicate["task_id"] == task_id,
                        duplicate,
                    )

                persistence = await factory.inspect(prepared, _uuid(task_id))
                record["persistence"] = persistence
                _assert_persistence(record, persistence, fixture.expected, task_id)
                record["outcome"] = "PASS"
            except Exception as exc:
                message = _safe_error(exc)
                record["error"] = message
                failures.append(f"{fixture.name}: {message}")
            finally:
                if prepared is not None:
                    try:
                        await factory.cleanup(prepared)
                    except Exception as exc:
                        message = _safe_error(exc)
                        record["cleanup_error"] = message
                        failures.append(f"{fixture.name} cleanup: {message}")
                        record["outcome"] = "FAIL"
                records.append(record)
    except Exception as exc:
        failures.append(f"harness: {_safe_error(exc)}")
    finally:
        if factory is not None:
            try:
                await factory.close()
            except Exception as exc:
                failures.append(f"harness cleanup: {_safe_error(exc)}")

    elapsed_ms = round((time.monotonic() - started) * 1000)
    passed = not failures and len(records) == 2 and all(
        record.get("outcome") == "PASS" for record in records
    )
    actual = {
        "scenario": "S-03 JD parse internal capability acceptance",
        "run_id": run_id,
        "started_at": started_at,
        "duration_ms": elapsed_ms,
        "fixtures": records,
        "passed": passed,
        "failures": failures,
    }
    _assert_artifact_is_safe(actual)
    (artifact_dir / "actual.json").write_text(
        json.dumps(actual, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (artifact_dir / "report.md").write_text(
        _render_report(actual), encoding="utf-8"
    )
    return {"passed": passed, "artifact_dir": str(artifact_dir), "actual": actual}


def _assert_artifact_is_safe(actual: dict[str, object]) -> None:
    serialized = json.dumps(actual, ensure_ascii=False)
    forbidden = (
        "Bearer ",
        "JWT_SECRET_KEY",
        "password",
        "storage_key",
        "/opt/careerpass/",
        ".careerpass-objects",
    )
    leaked = [marker for marker in forbidden if marker in serialized]
    if leaked:
        raise AssertionError("Acceptance Artifact contains restricted diagnostic data")


def _submit(client: httpx.Client, local_path: str) -> dict[str, object]:
    response = client.post(
        "/internal/v1/s03/job-description/parses", json={"local_path": local_path}
    )
    if response.status_code != 200:
        raise AssertionError(f"submit HTTP {response.status_code}")
    body = response.json()
    data = body.get("data")
    if not isinstance(data, dict) or not data.get("task_id"):
        raise AssertionError("submit response missing task_id")
    return data


def _poll_result(client: httpx.Client, task_id: str, record: dict[str, object]) -> dict[str, object]:
    deadline = time.monotonic() + float(os.environ.get("S03_ACCEPTANCE_TIMEOUT_SECONDS", "90"))
    while time.monotonic() < deadline:
        response = client.get(f"/internal/v1/s03/job-description/parses/{task_id}")
        if response.status_code != 200:
            raise AssertionError(f"status HTTP {response.status_code}")
        body = response.json()
        result = body.get("data")
        if not isinstance(result, dict):
            raise AssertionError("status response missing data")
        statuses = record.setdefault("task_statuses", [])
        if result.get("status") not in statuses:
            statuses.append(result.get("status"))
        if result.get("status") in TERMINAL_STATUSES:
            return result
        time.sleep(0.5)
    raise AssertionError("S-03 task did not reach a terminal status before timeout")


def _assert_parse_result(
    record: dict[str, object],
    actual: dict[str, object],
    expected: dict[str, object],
    content: bytes,
) -> None:
    _check(record, "status=succeeded", actual.get("status") == "succeeded", actual.get("status"))
    _check(
        record,
        "parse_status=succeeded",
        actual.get("parse_status") == "succeeded",
        actual.get("parse_status"),
    )
    _check(
        record,
        "matching_status=matching_ready",
        actual.get("matching_status") == "matching_ready",
        actual.get("matching_status"),
    )
    _check(record, "schema_version=v1", actual.get("schema_version") == "v1", actual.get("schema_version"))
    fields = actual.get("fields")
    if not isinstance(fields, dict):
        _check(record, "fields persisted", False, fields)
        return
    for field_name in ("title", "company_name", "location"):
        field = fields.get(field_name) or {}
        actual_value = field.get("raw") if isinstance(field, dict) else None
        _check(record, f"{field_name} matches Expected", actual_value == expected[field_name], actual_value)
    salary = fields.get("salary_range") or {}
    _check(record, "salary minimum matches Expected", salary.get("min") == expected["salary_min"], salary.get("min"))
    _check(record, "salary maximum matches Expected", salary.get("max") == expected["salary_max"], salary.get("max"))
    _check(record, "salary period matches Expected", salary.get("period") == expected["salary_period"], salary.get("period"))
    source = content.decode("utf-8")
    for section_name, expected_count in (
        ("responsibilities", expected["responsibilities_count"]),
        ("requirements", expected["requirements_count"]),
    ):
        section = fields.get(section_name) or {}
        items = section.get("items", []) if isinstance(section, dict) else []
        _check(record, f"{section_name} item count", len(items) == expected_count, len(items))
        raw = section.get("raw") if isinstance(section, dict) else None
        heading = "岗位职责" if section_name == "responsibilities" else "任职要求"
        expected_raw = _fixture_section_raw(source, heading)
        _check(record, f"{section_name} raw comes from fixture", raw == expected_raw, raw)
        for item in items:
            item_raw = item.get("raw") if isinstance(item, dict) else ""
            _check(record, f"{section_name} item is in fixture", bool(item_raw and item_raw in source), item_raw)
    additional = fields.get("additional_fields") or {}
    expected_keys = expected["additional_field_keys"]
    _check(record, "additional field keys preserved", sorted(additional) == sorted(expected_keys), sorted(additional))
    for heading in expected_keys:
        actual_extra = additional.get(heading) or {}
        expected_raw = _fixture_section_raw(source, heading)
        _check(
            record,
            f"additional field {heading} raw preserved",
            actual_extra.get("raw") == expected_raw,
            actual_extra.get("raw"),
        )


def _assert_persistence(
    record: dict[str, object],
    persistence: dict[str, object],
    expected: dict[str, object],
    task_id: str,
) -> None:
    _check(record, "Job belongs to hr_01 profile", bool(persistence.get("hr_profile_id")), persistence.get("hr_profile_id"))
    _check(record, "StoredFileObject is ready", persistence.get("file_object_status") == "ready", persistence.get("file_object_status"))
    _check(record, "task persisted as succeeded", persistence.get("task_status") == "succeeded", persistence.get("task_status"))
    _check(record, "snapshot persisted", bool(persistence.get("snapshot_id")), persistence.get("snapshot_id"))
    _check(record, "snapshot schema is v1", persistence.get("schema_version") == "v1", persistence.get("schema_version"))
    _check(record, "S-08 handoff is ready", persistence.get("handoff_ready") is True, persistence.get("handoff_ready"))
    _check(record, "one task exists after duplicate submit", persistence.get("task_count") == 1, persistence.get("task_count"))
    _check(record, "one snapshot exists after duplicate submit", persistence.get("snapshot_count") == 1, persistence.get("snapshot_count"))
    _check(record, "task id remains stable", persistence.get("task_id") == task_id, persistence.get("task_id"))
    fields = persistence.get("fields") or {}
    _check(record, "persisted fields contain title", bool(fields.get("title")), fields.get("title"))
    _check(record, "persisted fields contain responsibilities", bool(fields.get("responsibilities")), fields.get("responsibilities"))
    _check(record, "persisted fields contain requirements", bool(fields.get("requirements")), fields.get("requirements"))
    _check(record, "expected additional field count is represented", len(fields.get("additional_fields", {})) == len(expected["additional_field_keys"]), fields.get("additional_fields"))


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


def _uuid(value: object):
    from uuid import UUID

    return UUID(str(value))


def _safe_error(exc: Exception) -> str:
    return str(exc).replace("\r", " ").replace("\n", " ")[:240] or exc.__class__.__name__


def _render_report(actual: dict[str, object]) -> str:
    lines = [
        "# S-03 JD Parse Acceptance Report",
        "",
        f"- Result: **{'PASS' if actual['passed'] else 'FAIL'}**",
        f"- Run ID: `{actual['run_id']}`",
        f"- Duration: `{actual['duration_ms']} ms`",
        "- Entry: stable S-03 internal API",
        "- Scope: Factory → Dispatcher → Redis/Celery Worker → S-03 persistence and handoff",
        "",
    ]
    for record in actual["fixtures"]:
        lines.extend([f"## {record['fixture']}", "", f"Outcome: **{record['outcome']}**", ""])
        lines.append(f"Task statuses: `{', '.join(str(item) for item in record.get('task_statuses', []))}`")
        lines.append("")
        lines.append("| Assertion | Result | Actual |")
        lines.append("| --- | --- | --- |")
        for check in record.get("checks", []):
            lines.append(f"| {check['name']} | {check['status']} | `{_report_value(check.get('actual'))}` |")
        if record.get("error"):
            lines.extend(["", f"Failure: `{record['error']}`"])
        if record.get("cleanup_error"):
            lines.extend(["", f"Cleanup failure: `{record['cleanup_error']}`"])
        lines.append("")
    if actual["failures"]:
        lines.extend(["## Failure Summary", ""])
        lines.extend(f"- {failure}" for failure in actual["failures"])
    lines.extend(["", "完整机器可读实际结果见同目录 `actual.json`。"])
    return "\n".join(lines) + "\n"


def _report_value(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return text.replace("`", "'").replace("\n", " ")[:180]
