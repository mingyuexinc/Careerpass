from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_matching_service
from app.core.identity import CurrentIdentity
from app.main import create_app
from app.repositories.matching_repository import ApplicationQueryResult
from app.schemas.application import ApplicationItem


class FakeMatchingService:
    def __init__(self) -> None:
        self.candidate_id = None

    async def list_current_applications(self, *, candidate_id):
        self.candidate_id = candidate_id
        return ApplicationQueryResult(run=None, applications=[])


def _identity(*, role: str, candidate_id):
    return CurrentIdentity(
        user_id=uuid4(),
        username="candidate-demo",
        name="Demo Candidate",
        roles=(role,),
        active_role=role,
        candidate_id=candidate_id,
    )


def test_current_applications_uses_identity_and_uniform_envelope() -> None:
    app = create_app()
    service = FakeMatchingService()
    candidate_id = uuid4()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="candidate", candidate_id=candidate_id
    )
    app.dependency_overrides[get_matching_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/applications/current")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "msg": "success",
        "data": {"run": None, "applications": [], "total": 0},
    }
    assert service.candidate_id == candidate_id


def test_current_applications_rejects_non_candidate_identity() -> None:
    app = create_app()
    service = FakeMatchingService()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="hr", candidate_id=None
    )
    app.dependency_overrides[get_matching_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/applications/current")

    assert response.status_code == 403
    assert response.json()["data"] is None
    assert service.candidate_id is None


def test_application_item_contains_only_safe_match_projection() -> None:
    item = ApplicationItem(
        id=uuid4(), job_id=uuid4(), candidate_id=uuid4(), status="submitted",
        job_title="AI 应用开发工程师", company_name="受控公司", location="深圳",
        salary="25-40K", match_score=82,
        recommendation_reason="岗位画像高度匹配；技能匹配覆盖5/6项。",
        applied_at=datetime.now(UTC),
    )
    assert "recommendation_reason" in item.model_dump()
    assert "resume_text" not in item.model_dump()
