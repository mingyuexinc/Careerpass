from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_job_goal_service
from app.core.identity import CurrentIdentity
from app.main import create_app
from app.schemas.job_goal import CurrentJobGoalResponse, JobGoalResponse


def _identity(*, role: str, candidate_id: UUID | None) -> CurrentIdentity:
    return CurrentIdentity(
        user_id=uuid4(),
        username="candidate-demo",
        name="Demo Candidate",
        roles=(role,),
        active_role=role,
        candidate_id=candidate_id,
    )


class FakeJobGoalService:
    def __init__(self) -> None:
        self.goal = None
        self.save_calls = 0

    async def get_current(self, *, candidate_id: UUID) -> CurrentJobGoalResponse:
        return CurrentJobGoalResponse(goal=self.goal)

    async def save_current(self, *, candidate_id: UUID, value):
        self.save_calls += 1
        now = datetime.now(timezone.utc)
        self.goal = JobGoalResponse(
            id=self.goal.id if self.goal else uuid4(),
            offer_target=value.offer_target,
            title=value.title,
            filters=value.filters,
            status="active",
            created_at=self.goal.created_at if self.goal else now,
            updated_at=now,
        )
        return self.goal


def test_current_job_goal_api_creates_and_updates_same_goal() -> None:
    app = create_app()
    service = FakeJobGoalService()
    candidate_id = uuid4()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="candidate", candidate_id=candidate_id
    )
    app.dependency_overrides[get_job_goal_service] = lambda: service

    with TestClient(app) as client:
        created = client.put(
            "/api/v1/job_goals/current",
            json={"offer_target": 2, "title": "后端开发", "filters": ""},
        )
        goal_id = created.json()["data"]["goal"]["id"]
        updated = client.put(
            "/api/v1/job_goals/current",
            json={"offer_target": 3, "title": "全栈开发", "filters": "优先 AI"},
        )
        current = client.get("/api/v1/job_goals/current")

    assert created.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["data"]["goal"]["id"] == goal_id
    assert updated.json()["data"]["goal"]["offer_target"] == 3
    assert current.json()["data"]["goal"]["title"] == "全栈开发"
    assert service.save_calls == 2


def test_current_job_goal_api_rejects_non_candidate_before_service_call() -> None:
    app = create_app()
    service = FakeJobGoalService()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="hr", candidate_id=None
    )
    app.dependency_overrides[get_job_goal_service] = lambda: service

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/job_goals/current",
            json={"offer_target": 1, "title": "后端开发", "filters": ""},
        )

    assert response.status_code == 403
    assert response.json()["data"] is None
    assert service.save_calls == 0


def test_current_job_goal_api_rejects_invalid_payload() -> None:
    app = create_app()
    service = FakeJobGoalService()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="candidate", candidate_id=uuid4()
    )
    app.dependency_overrides[get_job_goal_service] = lambda: service

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/job_goals/current",
            json={"offer_target": 11, "title": "", "filters": ""},
        )

    assert response.status_code == 400
    assert response.json()["data"] is None
    assert service.save_calls == 0
