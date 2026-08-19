"""Unit coverage for the authenticated HR Job query projection."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_job_service
from app.core.identity import CurrentIdentity
from app.main import create_app
from app.schemas.job import HrJobItem


def _identity(*, role: str, hr_profile_id: UUID | None = None) -> CurrentIdentity:
    return CurrentIdentity(
        user_id=uuid4(),
        username="hr-demo",
        name="Mia Wang",
        roles=(role,),
        active_role=role,
        hr_profile_id=hr_profile_id,
    )


class FakeJobService:
    def __init__(self) -> None:
        self.hr_profile_id: UUID | None = None
        self.jobs = [
            HrJobItem(
                id=uuid4(),
                file_name="ai-engineer.md",
                job_title="AI 应用开发工程师",
                company_name="示例公司",
                created_at="2026-08-19T00:00:00Z",
                parse_status="succeeded",
            )
        ]

    async def list_current_for_hr(self, *, hr_profile_id: UUID) -> list[HrJobItem]:
        self.hr_profile_id = hr_profile_id
        return self.jobs


def test_current_hr_jobs_uses_identity_and_uniform_envelope() -> None:
    app = create_app()
    service = FakeJobService()
    hr_profile_id = uuid4()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="hr", hr_profile_id=hr_profile_id
    )
    app.dependency_overrides[get_job_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/jobs/hr/current")

    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert response.json()["msg"] == "current HR jobs"
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["jobs"][0]["job_title"] == "AI 应用开发工程师"
    assert response.json()["data"]["jobs"][0]["file_name"] == "ai-engineer.md"
    assert "storage_key" not in response.json()["data"]["jobs"][0]
    assert service.hr_profile_id == hr_profile_id


def test_current_hr_jobs_rejects_non_hr_identity() -> None:
    app = create_app()
    service = FakeJobService()
    app.dependency_overrides[get_current_identity] = lambda: _identity(role="candidate")
    app.dependency_overrides[get_job_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/jobs/hr/current")

    assert response.status_code == 403
    assert response.json()["data"] is None
    assert service.hr_profile_id is None
