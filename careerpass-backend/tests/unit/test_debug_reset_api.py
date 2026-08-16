"""API boundary tests for the development-only current-account reset."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_debug_reset_service
from app.core.identity import CurrentIdentity
from app.main import create_app
from app.services.debug_reset_service import (
    DebugResetDisabledError,
    ResetAccountBusyError,
    ResetAccountConflictError,
)


def _identity(role: str) -> CurrentIdentity:
    return CurrentIdentity(
        user_id=uuid4(),
        username=f"{role}-demo",
        name="Demo User",
        roles=(role,),
        active_role=role,
        candidate_id=uuid4() if role == "candidate" else None,
        hr_profile_id=uuid4() if role == "hr" else None,
    )


class FakeDebugResetService:
    def __init__(self, outcome: Exception | None = None) -> None:
        self.outcome = outcome
        self.calls: list[CurrentIdentity] = []

    async def reset_current_account(self, identity: CurrentIdentity) -> None:
        self.calls.append(identity)
        if self.outcome:
            raise self.outcome


def _client(service: FakeDebugResetService, role: str = "candidate") -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_identity] = lambda: _identity(role)
    app.dependency_overrides[get_debug_reset_service] = lambda: service
    return TestClient(app)


def test_debug_reset_api_uses_authenticated_current_identity() -> None:
    service = FakeDebugResetService()
    with _client(service, role="hr") as client:
        response = client.post("/api/v1/debug/reset/current-account")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "msg": "debug data reset",
        "data": {"reset": True, "scope": "current_account"},
    }
    assert service.calls[0].active_role == "hr"


def test_debug_reset_api_maps_disabled_and_busy_errors() -> None:
    for outcome, message in (
        (DebugResetDisabledError(), "debug reset is disabled"),
        (ResetAccountBusyError(), "reset is unavailable while account tasks are running"),
        (ResetAccountConflictError(), "account reset is blocked by dependent data"),
    ):
        service = FakeDebugResetService(outcome)
        with _client(service) as client:
            response = client.post("/api/v1/debug/reset/current-account")

        assert response.status_code == (403 if isinstance(outcome, DebugResetDisabledError) else 409)
        assert response.json()["data"] is None
        assert response.json()["msg"] == message
