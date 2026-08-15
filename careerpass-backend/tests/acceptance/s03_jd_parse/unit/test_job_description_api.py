"""Unit coverage for the S-03 internal API envelope and HR guard."""

import asyncio
from uuid import uuid4

import pytest

from app.api.v1.job_description import (
    _require_hr,
    get_job_description_parse,
    submit_job_description_parse,
)
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.job_description import (
    JobDescriptionParseResult,
    JobDescriptionParseSubmitData,
    JobDescriptionParseSubmitRequest,
)


def _identity(role="hr") -> CurrentIdentity:
    return CurrentIdentity(
        user_id=uuid4(),
        username="demo",
        name="Demo",
        roles=("hr",),
        active_role=role,
        hr_profile_id=uuid4() if role == "hr" else None,
    )


class FakeService:
    async def submit(self, **_):
        return JobDescriptionParseSubmitData(task_id=uuid4(), status="queued")

    async def get_result(self, **_):
        return JobDescriptionParseResult(
            task_id=uuid4(),
            job_id=uuid4(),
            status="succeeded",
            parse_status="succeeded",
            matching_status="matching_ready",
            snapshot_id=uuid4(),
            schema_version="v1",
            fields={
                "title": {"raw": "Role", "source_heading": "岗位名称", "source_order": 0},
                "location": {"raw": "上海", "source_heading": "工作地点", "source_order": 1},
                "salary_range": {"raw": "20k", "source_heading": "薪资", "source_order": 2},
                "responsibilities": {
                    "raw": "负责开发",
                    "items": [],
                    "source_heading": "岗位职责",
                    "source_order": 3,
                },
                "requirements": {
                    "raw": "熟悉 Python",
                    "items": [],
                    "source_heading": "任职要求",
                    "source_order": 4,
                },
            },
        )


def test_hr_guard_rejects_candidate_identity() -> None:
    with pytest.raises(AppException) as error:
        _require_hr(_identity("candidate"))
    assert error.value.status_code == 403


def test_internal_api_returns_uniform_envelopes() -> None:
    identity = _identity()
    service = FakeService()
    submitted = asyncio.run(
        submit_job_description_parse(
            payload=JobDescriptionParseSubmitRequest(local_path="/controlled/role.md"),
            identity=identity,
            service=service,  # type: ignore[arg-type]
        )
    )
    result = asyncio.run(
        get_job_description_parse(
            task_id=uuid4(),
            identity=identity,
            service=service,  # type: ignore[arg-type]
        )
    )

    assert submitted["code"] == 200
    assert submitted["data"]["status"] == "queued"
    assert result["code"] == 200
    assert result["data"]["matching_status"] == "matching_ready"
