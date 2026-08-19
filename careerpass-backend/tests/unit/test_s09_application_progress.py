"""Unit coverage for S-09 HR Application projection and status management."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_application_service
from app.core.identity import CurrentIdentity
from app.infrastructure.database.models import Application
from app.main import create_app
from app.repositories.application_repository import HrApplicationRecord
from app.schemas.application import (
    ApplicationStatusUpdateRequest,
    HrApplicationItem,
)
from app.services.application_service import (
    ApplicationService,
    ApplicationStatusConflictError,
    HrApplicationNotFoundError,
)


def _fields() -> dict[str, object]:
    text = {"raw": "示例", "normalized": "示例", "source_heading": "字段", "source_order": 0}
    section = {
        "raw": "示例",
        "items": [{"raw": "示例", "normalized": "示例", "source_order": 0}],
        "source_heading": "字段",
        "source_order": 0,
    }
    return {
        "title": {**text, "raw": "AI 应用开发工程师", "normalized": "AI 应用开发工程师"},
        "location": text,
        "salary_range": {
            "raw": "20K",
            "min": 20,
            "max": 20,
            "currency": "CNY",
            "period": "month",
            "source_heading": "薪资",
            "source_order": 0,
        },
        "responsibilities": section,
        "requirements": section,
        "company_name": {**text, "raw": "示例公司", "normalized": "示例公司"},
    }


def _record(*, status: str = "submitted", offer_target: int = 1) -> HrApplicationRecord:
    now = datetime.now(timezone.utc)
    application_id = uuid4()
    candidate_id = uuid4()
    return HrApplicationRecord(
        application=Application(
            id=application_id,
            candidate_id=candidate_id,
            job_id=uuid4(),
            run_id=uuid4(),
            match_id=uuid4(),
            status=status,
            applied_at=now,
            created_at=now,
            updated_at=now,
        ),
        job=SimpleNamespace(id=uuid4()),
        snapshot=SimpleNamespace(fields=_fields()),
        profile=SimpleNamespace(full_name="Alex Chen"),
        run=SimpleNamespace(id=uuid4(), status="running", finished_at=None, finish_reason=None),
        goal=SimpleNamespace(
            id=uuid4(), offer_target=offer_target, status="active", updated_at=now
        ),
    )


class FakeApplicationRepository:
    def __init__(self, record: HrApplicationRecord | None) -> None:
        self.record = record
        self.events: list[tuple[str, str]] = []
        self.offer_count = 0

    @asynccontextmanager
    async def transaction(self):
        yield

    async def list_current_for_hr(self, *, hr_profile_id: UUID):
        return [self._item()] if self.record else []

    async def get_for_hr_update(self, *, application_id: UUID, hr_profile_id: UUID):
        if self.record and self.record.application.id == application_id:
            return self.record
        return None

    async def append_status_event(self, *, record, from_status, to_status, now):
        self.events.append((from_status, to_status))

    async def count_offers(self, *, run_id: UUID, candidate_id: UUID) -> int:
        return self.offer_count

    async def finish_for_offer_target(self, *, record, offer_count, now):
        if record.run.status == "running" and offer_count >= record.goal.offer_target:
            record.run.status = "finished"
            record.run.finish_reason = "offer_target_reached"
            record.run.finished_at = now
            record.goal.status = "achieved"

    def _item(self):
        from app.repositories.application_repository import to_hr_item

        return to_hr_item(self.record)


def test_status_service_updates_event_and_offer_side_effects() -> None:
    record = _record(offer_target=1)
    repository = FakeApplicationRepository(record)
    repository.offer_count = 1

    value = asyncio.run(
        ApplicationService(repository=repository).update_status(
            application_id=record.application.id,
            hr_profile_id=uuid4(),
            status="offer",
        )
    )

    assert value.status == "offer"
    assert repository.events == [("submitted", "offer")]
    assert record.run.status == "finished"
    assert record.run.finish_reason == "offer_target_reached"
    assert record.goal.status == "achieved"


@pytest.mark.parametrize("current,next_status", [("screening", "submitted"), ("offer", "screening"), ("terminated", "offer")])
def test_status_service_rejects_backward_or_terminal_changes(current, next_status) -> None:
    record = _record(status=current)
    repository = FakeApplicationRepository(record)

    with pytest.raises(ApplicationStatusConflictError):
        asyncio.run(
            ApplicationService(repository=repository).update_status(
                application_id=record.application.id,
                hr_profile_id=uuid4(),
                status=next_status,
            )
        )
    assert repository.events == []


def test_same_status_is_idempotent_without_event() -> None:
    record = _record(status="offer")
    repository = FakeApplicationRepository(record)

    value = asyncio.run(
        ApplicationService(repository=repository).update_status(
            application_id=record.application.id,
            hr_profile_id=uuid4(),
            status="offer",
        )
    )

    assert value.status == "offer"
    assert repository.events == []


def _identity(*, role: str, hr_profile_id: UUID | None = None) -> CurrentIdentity:
    return CurrentIdentity(
        user_id=uuid4(),
        username="hr-demo",
        name="Mia Wang",
        roles=(role,),
        active_role=role,
        hr_profile_id=hr_profile_id,
    )


class FakeApplicationService:
    def __init__(self) -> None:
        self.application = HrApplicationItem(
            id=uuid4(),
            job_id=uuid4(),
            job_title="AI 应用开发工程师",
            company_name="示例公司",
            candidate_name="Alex Chen",
            status="submitted",
        )

    async def list_current_for_hr(self, *, hr_profile_id: UUID):
        return [self.application]

    async def update_status(self, *, application_id: UUID, hr_profile_id: UUID, status):
        if application_id != self.application.id:
            raise HrApplicationNotFoundError
        self.application = self.application.model_copy(update={"status": status})
        return self.application


def test_hr_application_api_uses_hr_identity_and_safe_projection() -> None:
    app = create_app()
    service = FakeApplicationService()
    hr_profile_id = uuid4()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="hr", hr_profile_id=hr_profile_id
    )
    app.dependency_overrides[get_application_service] = lambda: service
    listed_item = service.application.model_dump(mode="json")

    with TestClient(app) as client:
        listed = client.get("/api/v1/applications/hr/current")
        updated = client.patch(
            f"/api/v1/applications/{service.application.id}/status",
            json={"status": "screening"},
        )

    assert listed.status_code == 200
    assert listed.json()["data"]["applications"][0] == listed_item
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "screening"
    assert set(updated.json()["data"]) == {
        "id", "job_id", "job_title", "company_name", "candidate_name", "status"
    }


def test_hr_application_api_rejects_non_hr_identity() -> None:
    app = create_app()
    service = FakeApplicationService()
    app.dependency_overrides[get_current_identity] = lambda: _identity(role="candidate")
    app.dependency_overrides[get_application_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/applications/hr/current")

    assert response.status_code == 403
    assert response.json()["data"] is None


def test_application_status_schema_rejects_unknown_status_and_fields() -> None:
    with pytest.raises(ValueError):
        ApplicationStatusUpdateRequest(status="unknown")
    with pytest.raises(ValueError):
        ApplicationStatusUpdateRequest(status="screening", extra="blocked")
