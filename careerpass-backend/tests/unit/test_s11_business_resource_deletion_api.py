"""API coverage for the S-11 deletion command boundaries."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_business_resource_deletion_service
from app.core.identity import CurrentIdentity
from app.main import create_app
from app.repositories.business_resource_deletion_repository import DeletionNotAllowedError
from app.repositories.business_resource_deletion_repository import ResourceDeletionResult


def _identity(role: str) -> CurrentIdentity:
    return CurrentIdentity(
        user_id=uuid4(),
        username=f"{role}-demo",
        name="Demo",
        roles=(role,),
        active_role=role,
        candidate_id=uuid4() if role == "candidate" else None,
        hr_profile_id=uuid4() if role == "hr" else None,
    )


class FakeDeletionService:
    def __init__(self) -> None:
        self.result = ResourceDeletionResult("resume", uuid4(), True)
        self.calls: list[tuple[str, UUID]] = []
        self.reject = False

    async def delete_resume(self, **kwargs):
        if self.reject:
            raise DeletionNotAllowedError
        self.calls.append(("resume", kwargs["resume_id"]))
        return self.result

    async def delete_candidate_document(self, **kwargs):
        if self.reject:
            raise DeletionNotAllowedError
        self.calls.append(("candidate_document", kwargs["document_id"]))
        return ResourceDeletionResult("candidate_document", kwargs["document_id"], True)

    async def delete_job(self, **kwargs):
        if self.reject:
            raise DeletionNotAllowedError
        self.calls.append(("job", kwargs["job_id"]))
        return ResourceDeletionResult("job", kwargs["job_id"], True)


def test_candidate_can_delete_resume_and_document_through_uniform_envelopes() -> None:
    app = create_app()
    service = FakeDeletionService()
    identity = _identity("candidate")
    app.dependency_overrides[get_current_identity] = lambda: identity
    app.dependency_overrides[get_business_resource_deletion_service] = lambda: service

    resume_id = uuid4()
    document_id = uuid4()
    with TestClient(app) as client:
        resume_response = client.delete(f"/api/v1/resumes/{resume_id}")
        document_response = client.delete(f"/api/v1/candidate_documents/{document_id}")

    assert resume_response.status_code == 200
    assert resume_response.json()["data"] == {
        "resource_type": "resume",
        "resource_id": str(service.result.resource_id),
        "deleted": True,
    }
    assert document_response.status_code == 200
    assert document_response.json()["data"]["resource_type"] == "candidate_document"
    assert service.calls == [("resume", resume_id), ("candidate_document", document_id)]


def test_hr_can_delete_job_and_candidate_cannot_use_hr_command() -> None:
    app = create_app()
    service = FakeDeletionService()
    hr_identity = _identity("hr")
    app.dependency_overrides[get_current_identity] = lambda: hr_identity
    app.dependency_overrides[get_business_resource_deletion_service] = lambda: service

    job_id = uuid4()
    with TestClient(app) as client:
        response = client.delete(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["data"]["resource_type"] == "job"
    assert service.calls == [("job", job_id)]

    app.dependency_overrides[get_current_identity] = lambda: _identity("candidate")
    with TestClient(app) as client:
        forbidden = client.delete(f"/api/v1/jobs/{job_id}")
    assert forbidden.status_code == 403
    assert forbidden.json()["data"] is None


def test_deletion_state_failure_is_returned_as_conflict() -> None:
    app = create_app()
    service = FakeDeletionService()
    service.reject = True
    app.dependency_overrides[get_current_identity] = lambda: _identity("candidate")
    app.dependency_overrides[get_business_resource_deletion_service] = lambda: service

    with TestClient(app) as client:
        response = client.delete(f"/api/v1/resumes/{uuid4()}")

    assert response.status_code == 409
    assert response.json()["code"] == 409
    assert response.json()["data"] is None
