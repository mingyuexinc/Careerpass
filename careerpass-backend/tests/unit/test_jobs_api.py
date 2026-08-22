"""API-level tests for the authenticated S-02 upload boundary."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_job_description_service, get_job_upload_service
from app.core.identity import CurrentIdentity
from app.main import create_app
from app.schemas.job_description import JobDescriptionParseRetryData
from app.schemas.job_upload import JobUploadResponse, JobUploadResult


class FakeJobUploadService:
    def __init__(self) -> None:
        self.hr_profile_id = None
        self.upload_count = 0

    async def upload_many(self, *, hr_profile_id, uploads):
        self.hr_profile_id = hr_profile_id
        self.upload_count = len(uploads)
        return JobUploadResponse(
            results=[
                JobUploadResult(
                    index=index,
                    outcome="created",
                    job_id=uuid4(),
                    task_status="queued",
                )
                for index in range(len(uploads))
            ]
        )


class FakeJobDescriptionService:
    def __init__(self) -> None:
        self.call = None

    async def retry_failed_job(self, *, hr_profile_id, job_id):
        self.call = (hr_profile_id, job_id)
        return JobDescriptionParseRetryData(job_id=job_id, task_id=uuid4(), status="queued")


def _identity(*, role: str, hr_profile_id):
    return CurrentIdentity(
        user_id=uuid4(),
        username="hr-demo",
        name="Demo HR",
        roles=(role,),
        active_role=role,
        hr_profile_id=hr_profile_id,
    )


def test_jobs_upload_returns_per_file_results_and_uses_server_identity() -> None:
    app = create_app()
    service = FakeJobUploadService()
    hr_profile_id = uuid4()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="hr", hr_profile_id=hr_profile_id
    )
    app.dependency_overrides[get_job_upload_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/jobs",
            files=[
                ("files", ("first.md", b"# first", "text/markdown")),
                ("files", ("second.md", b"# second", "text/markdown")),
            ],
        )

    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert len(response.json()["data"]["results"]) == 2
    assert service.hr_profile_id == hr_profile_id
    assert service.upload_count == 2


def test_jobs_upload_rejects_non_hr_identity_before_service_call() -> None:
    app = create_app()
    service = FakeJobUploadService()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="candidate", hr_profile_id=None
    )
    app.dependency_overrides[get_job_upload_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/jobs",
            files=[("files", ("role.md", b"# role", "text/markdown"))],
        )

    assert response.status_code == 403
    assert response.json()["data"] is None
    assert service.upload_count == 0


def test_job_parse_retry_uses_owned_hr_identity() -> None:
    app = create_app()
    upload_service = FakeJobUploadService()
    parse_service = FakeJobDescriptionService()
    hr_profile_id = uuid4()
    job_id = uuid4()
    app.dependency_overrides[get_current_identity] = lambda: _identity(
        role="hr", hr_profile_id=hr_profile_id
    )
    app.dependency_overrides[get_job_upload_service] = lambda: upload_service
    app.dependency_overrides[get_job_description_service] = lambda: parse_service

    with TestClient(app) as client:
        response = client.post(f"/api/v1/jobs/{job_id}/parse/retry")

    assert response.status_code == 200
    assert response.json()["data"]["job_id"] == str(job_id)
    assert parse_service.call == (hr_profile_id, job_id)
