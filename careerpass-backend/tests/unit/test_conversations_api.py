"""Safe HR-facing S10-01 API projections and role boundary."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_conversation_service
from app.core.identity import CurrentIdentity
from app.main import create_app
from app.schemas.conversation import (
    AgentTurnView,
    ConversationView,
    MessageView,
    SendMessageResponse,
)


def _identity(role: str, hr_profile_id=None) -> CurrentIdentity:
    return CurrentIdentity(
        user_id=uuid4(),
        username="hr-demo",
        name="HR Demo",
        roles=(role,),
        active_role=role,
        hr_profile_id=hr_profile_id,
    )


class FakeConversationService:
    def __init__(self) -> None:
        self.hr_profile_id = None

    async def list_current_for_hr(self, *, hr_profile_id):
        self.hr_profile_id = hr_profile_id
        return [
            ConversationView(
                id=uuid4(),
                application_id=uuid4(),
                job_title="受控岗位",
                candidate_name="候选人甲",
                messages=[],
            )
        ]

    async def send_message(self, **kwargs):
        message = MessageView(
            id=uuid4(),
            sender="hr",
            message_type="text",
            status="sent",
            content=kwargs["content"],
            created_at=datetime.now(UTC),
        )
        return SendMessageResponse(
            conversation_id=kwargs["conversation_id"],
            received_message=message,
            agent_turn=AgentTurnView(
                id=uuid4(),
                scene="resume_answer",
                turn_status="completed",
                outcome="message_sent",
                retryable=False,
            ),
            new_messages=[],
        )

    async def download_attachment(self, **kwargs):
        return SimpleNamespace(
            content=b"non-zero attachment fixture",
            media_type="application/pdf",
            file_name="certificate.pdf",
        )


def test_hr_conversation_list_uses_identity_and_safe_projection() -> None:
    app = create_app()
    service = FakeConversationService()
    hr_profile_id = uuid4()
    app.dependency_overrides[get_current_identity] = lambda: _identity("hr", hr_profile_id)
    app.dependency_overrides[get_conversation_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/applications/hr/current/conversations")

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert service.hr_profile_id == hr_profile_id
    assert "resume_text" not in response.text
    assert "prompt" not in response.text.lower()


def test_non_hr_cannot_use_conversation_endpoint() -> None:
    app = create_app()
    service = FakeConversationService()
    app.dependency_overrides[get_current_identity] = lambda: _identity("candidate")
    app.dependency_overrides[get_conversation_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/applications/hr/current/conversations")

    assert response.status_code == 403
    assert response.json()["data"] is None


def test_attachment_download_returns_file_stream_without_internal_fields() -> None:
    app = create_app()
    service = FakeConversationService()
    hr_profile_id = uuid4()
    app.dependency_overrides[get_current_identity] = lambda: _identity("hr", hr_profile_id)
    app.dependency_overrides[get_conversation_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/applications/{uuid4()}/conversation/messages/{uuid4()}"
            f"/attachments/{uuid4()}/download"
        )

    assert response.status_code == 200
    assert response.content == b"non-zero attachment fixture"
    assert response.headers["content-type"] == "application/pdf"
    assert "certificate.pdf" in response.headers["content-disposition"]
    assert "storage_key" not in response.text
    assert "candidate_document_id" not in response.text
