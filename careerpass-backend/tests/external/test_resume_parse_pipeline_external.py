"""Explicit-cost, container-topology acceptance for the resume parsing pipeline."""

import os
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.external_integration

_POLL_INTERVAL_SECONDS = 2
_PIPELINE_TIMEOUT_SECONDS = 150


def test_controlled_resume_reaches_validated_atomic_terminal_state() -> None:
    """Assert only safe status and schema facts for one controlled resume."""
    if os.getenv("RUN_EXTERNAL_INTEGRATION_TESTS") != "true":
        pytest.skip("external resume parsing integration is disabled")
    if os.getenv("RUN_RESUME_PARSE_PIPELINE_TESTS") != "true":
        pytest.skip("external resume parsing pipeline acceptance is disabled")

    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "candidate_preparation"
        / "resumes"
        / "resume_1.pdf"
    )
    api_base_url = os.getenv("EXTERNAL_PIPELINE_API_BASE_URL", "http://localhost:8080")
    username = f"external-pipeline-{uuid4()}"

    with httpx.Client(base_url=api_base_url, timeout=10) as client:
        assert client.get("/health/ready").status_code == 200
        registration = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "StrongPassword123!"},
        )
        assert registration.status_code == 200
        token = registration.json()["data"]["access_token"]
        upload = client.post(
            "/api/v1/resumes",
            files={"file": ("controlled-resume.pdf", fixture.read_bytes(), "application/pdf")},
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid4())},
        )
        assert upload.status_code == 201
        resume_id = upload.json()["data"]["resume_id"]

        deadline = time.monotonic() + _PIPELINE_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            listed = client.get("/api/v1/resumes", headers={"Authorization": f"Bearer {token}"})
            assert listed.status_code == 200
            resume = next(item for item in listed.json()["data"]["list"] if item["resume_id"] == resume_id)
            if resume["parse_status"] == "succeeded":
                break
            if resume["parse_status"] == "failed":
                pytest.fail(f"controlled pipeline failed with {resume['failure_code']}")
            time.sleep(_POLL_INTERVAL_SECONDS)
        else:
            pytest.fail("controlled pipeline did not reach a terminal state before timeout")

        profile = client.get(
            f"/api/v1/resumes/{resume_id}/profile", headers={"Authorization": f"Bearer {token}"}
        )
        assert profile.status_code == 200
        data = profile.json()["data"]
        assert data["resume_id"] == resume_id
        assert data["target_job_titles"]
