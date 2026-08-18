"""Optional integration tests against isolated PostgreSQL and Redis services."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.infrastructure.cache import create_redis_client
from app.infrastructure.database import create_database
from app.infrastructure.database.models import (
    AsyncTaskRun,
    CandidateDocument,
    CandidateProfile,
    HrProfile,
    Job,
    Resume,
    StoredFileObject,
    User,
)
from app.infrastructure.storage import LocalObjectStorage
from app.infrastructure.tasks.celery_app import create_celery_app
from app.infrastructure.tasks.dispatcher import TaskDispatcher, celery_publication
from app.main import create_app
from app.repositories import CandidateRepository, UserRepository
from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.document_parsing_repository import DocumentParsingRepository
from app.repositories.object_storage_repository import ObjectStorageRepository
from app.schemas.document_parsing import ResumeProfileExtractionV1
from app.services.object_cleanup_service import ObjectCleanupService
from app.services.resume_parse_finalization_service import ResumeParseFinalizationService

pytestmark = pytest.mark.integration


def _require_integration_environment() -> tuple[str, str]:
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("set RUN_INTEGRATION_TESTS=true after starting the integration compose stack")
    database_url = os.getenv("TEST_DATABASE_URL")
    redis_url = os.getenv("TEST_REDIS_URL")
    if not database_url or not redis_url:
        pytest.skip("TEST_DATABASE_URL and TEST_REDIS_URL are required for integration tests")
    return database_url, redis_url


def test_migrations_are_repeatable_and_readiness_is_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url, redis_url = _require_integration_environment()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")
        # A fresh Compose database starts at the Alembic base revision. Establish
        # the current head before exercising downgrade/upgrade repeatability.
        command.upgrade(config, "head")
        command.downgrade(config, "20260725_0002")
        command.upgrade(config, "head")
        command.downgrade(config, "20260725_0002")
        command.upgrade(config, "head")

        async def assert_identity_schema_and_repositories() -> None:
            database = create_database(database_url)
            try:
                async with database.session_factory() as session:
                    tables = await session.execute(
                        text(
                            "SELECT to_regclass('public.users'), to_regclass('public.candidates'), "
                            "to_regclass('public.stored_file_objects'), to_regclass('public.resumes'), "
                            "to_regclass('public.candidate_profiles'), "
                            "to_regclass('public.candidate_documents'), "
                            "to_regclass('public.async_task_runs')"
                        )
                    )
                    assert tables.one() == (
                        "users",
                        "candidates",
                        "stored_file_objects",
                        "resumes",
                        "candidate_profiles",
                        "candidate_documents",
                        "async_task_runs",
                    )

                    triggers = await session.execute(
                        text(
                            """
                            SELECT tgname
                            FROM pg_trigger
                            WHERE tgname IN (
                                'trg_users_set_updated_at',
                                'trg_candidates_set_updated_at',
                                'trg_stored_file_objects_set_updated_at'
                            )
                            ORDER BY tgname
                            """
                        )
                    )
                    assert [row.tgname for row in triggers] == [
                        "trg_candidates_set_updated_at",
                        "trg_stored_file_objects_set_updated_at",
                        "trg_users_set_updated_at",
                    ]

                    constraints = await session.execute(
                        text(
                            "SELECT conname FROM pg_constraint WHERE conname IN ("
                            "'ck_stored_file_objects_ck_stored_file_size', "
                                "'ck_candidate_profiles_ck_candidate_profile_matching_readiness', "
                                "'ck_candidate_profiles_ck_candidate_profile_experience_duration', "
                            "'ck_async_task_runs_ck_async_task_run_finished_at', "
                            "'ck_async_task_runs_ck_async_task_run_failure_code') ORDER BY conname"
                        )
                    )
                    assert [row.conname for row in constraints] == [
                        "ck_async_task_runs_ck_async_task_run_failure_code",
                        "ck_async_task_runs_ck_async_task_run_finished_at",
                        "ck_candidate_profiles_ck_candidate_profile_experience_duration",
                        "ck_candidate_profiles_ck_candidate_profile_matching_readiness",
                        "ck_stored_file_objects_ck_stored_file_size",
                    ]

                async with database.session_factory() as session:
                    users = UserRepository(session)
                    candidates = CandidateRepository(session)
                    username = f"integration-{uuid4()}"
                    user, candidate = await users.create_with_candidate(
                        username=username,
                        password_hash="scrypt$integration-test-only",
                        name="Integration Candidate",
                    )

                    assert await users.get_by_id(user.id) is not None
                    assert await users.get_by_username(username) is not None
                    resolved_candidate = await candidates.get_by_user_id(user.id)
                    assert resolved_candidate is not None
                    assert resolved_candidate.id == candidate.id
            finally:
                await database.close()

        asyncio.run(assert_identity_schema_and_repositories())

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            username = f"api-{uuid4()}"
            register_response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": username,
                    "password": "StrongPassword123!",
                    "name": "Integration Candidate",
                },
            )
            assert register_response.status_code == 200
            access_token = register_response.json()["data"]["access_token"]

            duplicate_response = client.post(
                "/api/v1/auth/register",
                json={"username": username, "password": "StrongPassword123!"},
            )
            assert duplicate_response.status_code == 409

            login_response = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "StrongPassword123!"},
            )
            assert login_response.status_code == 200

            me_response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me_response.status_code == 200
            assert me_response.json()["data"]["username"] == username

            invalid_login_response = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "WrongPassword123!"},
            )
            assert invalid_login_response.status_code == 401

            response = client.get("/health/ready")

        assert response.status_code == 200
        assert response.json() == {
            "code": 200,
            "msg": "success",
            "data": {"status": "ready"},
        }
    finally:
        get_settings.cache_clear()


def test_candidate_preparation_upload_reuses_objects_without_orphans(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database_url, redis_url = _require_integration_environment()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(tmp_path / "objects"))
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            username = f"upload-{uuid4()}"
            registration = client.post(
                "/api/v1/auth/register",
                json={"username": username, "password": "StrongPassword123!"},
            )
            token = registration.json()["data"]["access_token"]
            candidate_id = registration.json()["data"]["user"]["candidate_id"]
            headers = {
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": str(uuid4()),
            }
            files = {
                "file": (
                    "resume.pdf",
                    f"%PDF-1.7\n{username}".encode(),
                    "application/pdf",
                )
            }
            first = client.post("/api/v1/resumes", files=files, headers=headers)
            replay = client.post("/api/v1/resumes", files=files, headers=headers)
            second = client.post(
                "/api/v1/resumes",
                files=files,
                headers={"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid4())},
            )
            object_storage_root = app.state.object_storage._root

        assert first.status_code == replay.status_code == 201
        assert second.status_code == 409
        assert first.json()["data"]["resume_id"] == replay.json()["data"]["resume_id"]
        assert len(list(object_storage_root.iterdir())) == 1

        async def assert_object_reuse() -> None:
            database = create_database(database_url)
            try:
                async with database.session_factory() as session:
                    counts = await session.execute(
                        text(
                            "SELECT (SELECT count(*) FROM resumes WHERE candidate_id = :candidate_id), "
                            "(SELECT count(DISTINCT stored_file_object_id) FROM resumes "
                            "WHERE candidate_id = :candidate_id), "
                            "(SELECT count(*) FROM stored_file_objects o WHERE EXISTS "
                            "(SELECT 1 FROM resumes r WHERE r.candidate_id = :candidate_id "
                            "AND r.stored_file_object_id = o.id) AND NOT EXISTS "
                            "(SELECT 1 FROM resumes r2 WHERE r2.stored_file_object_id = o.id))"
                        ),
                        {"candidate_id": candidate_id},
                    )
                    # S-04 reuses the same candidate-owned Resume for identical PDF
                    # content, even when the request uses a different idempotency key.
                    assert counts.one() == (1, 1, 0)
            finally:
                await database.close()

        asyncio.run(assert_object_reuse())
    finally:
        get_settings.cache_clear()


def test_candidate_preparation_apis_enforce_contract_and_candidate_isolation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exercise the public upload APIs against real persistence and object storage."""
    database_url, redis_url = _require_integration_environment()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(tmp_path / "objects"))
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            first_registration = client.post(
                "/api/v1/auth/register",
                json={"username": f"candidate-a-{uuid4()}", "password": "StrongPassword123!"},
            )
            second_registration = client.post(
                "/api/v1/auth/register",
                json={"username": f"candidate-b-{uuid4()}", "password": "StrongPassword123!"},
            )
            first_headers = {
                "Authorization": f"Bearer {first_registration.json()['data']['access_token']}",
                "Idempotency-Key": str(uuid4()),
            }
            second_headers = {
                "Authorization": f"Bearer {second_registration.json()['data']['access_token']}"
            }
            resume_files = {"file": ("resume.pdf", b"%PDF-1.7\\nCandidate A", "application/pdf")}
            created_resume = client.post(
                "/api/v1/resumes",
                files=resume_files,
                data={"name": "candidate-a-resume.pdf"},
                headers=first_headers,
            )
            replayed_resume = client.post(
                "/api/v1/resumes",
                files=resume_files,
                data={"name": "candidate-a-resume.pdf"},
                headers=first_headers,
            )
            conflicting_resume = client.post(
                "/api/v1/resumes",
                files={"file": ("resume.pdf", b"%PDF-1.7\\nChanged", "application/pdf")},
                data={"name": "candidate-a-resume.pdf"},
                headers=first_headers,
            )
            invalid_resume = client.post(
                "/api/v1/resumes",
                files={"file": ("resume.txt", b"not a PDF", "text/plain")},
                headers={"Authorization": first_headers["Authorization"]},
            )

            other_resumes = client.get("/api/v1/resumes", headers=second_headers)
            own_resumes = client.get(
                "/api/v1/resumes", headers={"Authorization": first_headers["Authorization"]}
            )

            document_headers = {
                "Authorization": first_headers["Authorization"],
                "Idempotency-Key": str(uuid4()),
            }
            created_document = client.post(
                "/api/v1/candidate_documents",
                files=[
                    ("files", ("certificate.md", b"# Certificate", "text/markdown")),
                    ("files", ("portfolio.pdf", b"%PDF-1.7\nPortfolio", "application/pdf")),
                    ("files", ("unsupported.docx", b"not supported", "application/octet-stream")),
                ],
                headers=document_headers,
            )
            duplicate_document = client.post(
                "/api/v1/candidate_documents",
                files=[("files", ("renamed.pdf", b"%PDF-1.7\nPortfolio", "application/pdf"))],
                headers={
                    "Authorization": first_headers["Authorization"],
                    "Idempotency-Key": str(uuid4()),
                },
            )
            own_documents = client.get(
                "/api/v1/candidate_documents",
                headers={"Authorization": first_headers["Authorization"]},
            )
            other_documents = client.get("/api/v1/candidate_documents", headers=second_headers)
            unavailable_profile = client.get(
                f"/api/v1/resumes/{created_resume.json()['data']['resume_id']}/profile",
                headers=second_headers,
            )

        assert created_resume.status_code == replayed_resume.status_code == 201
        assert created_resume.json()["code"] == 201
        assert created_resume.json()["msg"] == "上传已受理，正在解析简历"
        assert created_resume.json()["data"]["parse_status"] == "processing"
        assert created_resume.json()["data"]["resume_id"] == replayed_resume.json()["data"]["resume_id"]
        assert conflicting_resume.status_code == 409
        assert conflicting_resume.json()["code"] == 409
        assert conflicting_resume.json()["data"] is None
        assert invalid_resume.status_code == 400
        assert invalid_resume.json()["code"] == 400

        assert own_resumes.status_code == 200
        assert own_resumes.json()["data"]["total"] == 1
        assert own_resumes.json()["data"]["list"][0]["name"] == "candidate-a-resume.pdf"
        assert own_resumes.json()["data"]["list"][0]["parse_status"] == "processing"
        assert other_resumes.status_code == 200
        assert other_resumes.json()["data"]["list"] == []

        assert created_document.status_code == 200
        created_results = created_document.json()["data"]["results"]
        assert created_document.json()["code"] == 200
        assert created_document.json()["msg"] == "其它资料已就绪。"
        assert [result["result"] for result in created_results] == [
            "created",
            "created",
            "failed",
        ]
        assert [result["upload_status"] for result in created_results] == [
            "success",
            "success",
            "failed",
        ]
        assert created_results[2]["failure_code"] == "unsupported_file"
        assert all(result["candidate_document_id"] for result in created_results[:2])
        assert duplicate_document.status_code == 200
        duplicate_result = duplicate_document.json()["data"]["results"][0]
        assert duplicate_result["result"] == "duplicate"
        assert duplicate_result["upload_status"] == "success"
        assert duplicate_result["candidate_document_id"] == created_results[1]["candidate_document_id"]
        assert own_documents.json()["data"]["total"] == 2
        assert {item["file_type"] for item in own_documents.json()["data"]["list"]} == {"md", "pdf"}
        for document_item in own_documents.json()["data"]["list"]:
            assert document_item["upload_status"] == "success"
            assert "version" not in document_item
            assert "storage_key" not in document_item
            assert "content" not in document_item
        assert other_documents.json()["data"]["list"] == []
        assert unavailable_profile.status_code == 404
        assert unavailable_profile.json()["code"] == 404
    finally:
        get_settings.cache_clear()


def test_dispatcher_and_execution_leases_use_real_postgres_and_redis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify publication recovery and late-worker protection with actual dependencies."""
    database_url, redis_url = _require_integration_environment()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(tmp_path / "objects"))
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            registration = client.post(
                "/api/v1/auth/register",
                json={"username": f"dispatch-{uuid4()}", "password": "StrongPassword123!"},
            )
            upload = client.post(
                "/api/v1/resumes",
                files={"file": ("resume.pdf", b"%PDF-1.7\\nDispatcher", "application/pdf")},
                headers={
                    "Authorization": f"Bearer {registration.json()['data']['access_token']}",
                    "Idempotency-Key": str(uuid4()),
                },
            )
            resume_id = upload.json()["data"]["resume_id"]
            queue_name = f"integration-dispatch-{uuid4()}"
            dispatcher_database = create_database(database_url)
            celery_app = create_celery_app(redis_url, task_time_limit_seconds=30)
            celery_app.conf.task_default_queue = queue_name
            dispatcher = TaskDispatcher(
                database=dispatcher_database,
                lease_seconds=30,
                batch_size=20,
                publish=celery_publication(celery_app),
            )

            async def verify_dispatch_and_leases() -> None:
                try:
                    async with dispatcher_database.session_factory() as session:
                        task_run = await session.scalar(
                            select(AsyncTaskRun).where(AsyncTaskRun.resource_id == UUID(resume_id))
                        )
                        assert task_run is not None
                        assert task_run.task_type == "resume_parse"
                        assert task_run.resource_type == "resume"
                        assert task_run.task_version == "v1"
                        assert task_run.status == "queued"
                        task_run_id = task_run.id

                    assert await dispatcher.dispatch_once() >= 1
                    assert await dispatcher.dispatch_once() == 0

                    redis_client = create_redis_client(redis_url)
                    try:
                        assert await redis_client.client.llen(queue_name) >= 1
                        await redis_client.client.delete(queue_name)
                    finally:
                        await redis_client.close()

                    async with dispatcher_database.session_factory() as session:
                        repository = AsyncTaskRepository(session)
                        first_lease = await repository.claim_execution(
                            task_run_id=task_run_id, lease_seconds=90
                        )
                        assert first_lease is not None
                        assert await repository.claim_execution(task_run_id=task_run_id, lease_seconds=90) is None
                        assert await repository.release_execution_for_retry(
                            task_run_id=task_run_id,
                            execution_token=first_lease.execution_token,
                        )

                    async with dispatcher_database.session_factory() as session:
                        repository = AsyncTaskRepository(session)
                        second_lease = await repository.claim_execution(
                            task_run_id=task_run_id, lease_seconds=90
                        )
                        assert second_lease is not None
                        assert not await repository.release_execution_for_retry(
                            task_run_id=task_run_id,
                            execution_token=first_lease.execution_token,
                        )
                        await session.execute(
                            text(
                                "UPDATE async_task_runs SET started_at = CURRENT_TIMESTAMP - INTERVAL '11 minutes', "
                                "execution_lease_expires_at = CURRENT_TIMESTAMP - INTERVAL '1 second' "
                                "WHERE id = :task_run_id"
                            ),
                            {"task_run_id": task_run_id},
                        )
                        await session.commit()

                    assert await dispatcher.recover_stalled_once() >= 1
                    async with dispatcher_database.session_factory() as session:
                        task_run = await session.get(AsyncTaskRun, task_run_id)
                        assert task_run is not None
                        assert task_run.status == "failed"
                        assert task_run.failure_code == "internal_error"
                        resume = await session.get(Resume, UUID(resume_id))
                        assert resume is not None
                        assert resume.parse_status == "failed"
                finally:
                    await dispatcher_database.close()

            asyncio.run(verify_dispatch_and_leases())
    finally:
        get_settings.cache_clear()


def test_resume_parse_terminal_states_are_atomic_and_lease_guarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Use real PostgreSQL to prove profiles and both terminal states share their lease guard."""
    database_url, redis_url = _require_integration_environment()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(tmp_path / "objects"))
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            registration = client.post(
                "/api/v1/auth/register",
                json={"username": f"terminal-{uuid4()}", "password": "StrongPassword123!"},
            )
            headers = {"Authorization": f"Bearer {registration.json()['data']['access_token']}"}
            failure_registration = client.post(
                "/api/v1/auth/register",
                json={"username": f"terminal-failure-{uuid4()}", "password": "StrongPassword123!"},
            )
            failure_headers = {
                "Authorization": f"Bearer {failure_registration.json()['data']['access_token']}"
            }
            success_upload = client.post(
                "/api/v1/resumes",
                files={"file": ("success.pdf", b"%PDF-1.7\nsuccess", "application/pdf")},
                headers={**headers, "Idempotency-Key": str(uuid4())},
            )
            failure_upload = client.post(
                "/api/v1/resumes",
                files={"file": ("failure.pdf", b"%PDF-1.7\nfailure", "application/pdf")},
                headers={**failure_headers, "Idempotency-Key": str(uuid4())},
            )
        assert success_upload.status_code == failure_upload.status_code == 201
        success_resume_id = UUID(success_upload.json()["data"]["resume_id"])
        failure_resume_id = UUID(failure_upload.json()["data"]["resume_id"])

        async def verify_terminal_states() -> None:
            database = create_database(database_url)
            try:
                async with database.session_factory() as session:
                    success_task = await session.scalar(
                        select(AsyncTaskRun).where(AsyncTaskRun.resource_id == success_resume_id)
                    )
                    failure_task = await session.scalar(
                        select(AsyncTaskRun).where(AsyncTaskRun.resource_id == failure_resume_id)
                    )
                    assert success_task is not None and failure_task is not None

                async with database.session_factory() as session:
                    lease = await AsyncTaskRepository(session).claim_execution(
                        task_run_id=success_task.id, lease_seconds=90
                    )
                    assert lease is not None

                async with database.session_factory() as session:
                    service = ResumeParseFinalizationService(
                        repository=DocumentParsingRepository(session)
                    )
                    assert await service.succeed(
                        lease,
                        ResumeProfileExtractionV1(target_job_titles=["Backend Engineer"]),
                    )
                    assert not await service.fail(lease, "internal_error")

                async with database.session_factory() as session:
                    resume = await session.get(Resume, success_resume_id)
                    task = await session.get(AsyncTaskRun, success_task.id)
                    profile = await session.scalar(
                        select(CandidateProfile).where(CandidateProfile.resume_id == success_resume_id)
                    )
                    assert resume is not None and resume.parse_status == "succeeded"
                    assert task is not None and task.status == "succeeded" and task.finished_at is not None
                    assert task.execution_token is None and task.execution_lease_expires_at is None
                    assert profile is not None and profile.target_job_titles == ["Backend Engineer"]

                async with database.session_factory() as session:
                    failure_lease = await AsyncTaskRepository(session).claim_execution(
                        task_run_id=failure_task.id, lease_seconds=90
                    )
                    assert failure_lease is not None

                async with database.session_factory() as session:
                    service = ResumeParseFinalizationService(
                        repository=DocumentParsingRepository(session)
                    )
                    assert await service.fail(failure_lease, "schema_validation_failed")

                async with database.session_factory() as session:
                    resume = await session.get(Resume, failure_resume_id)
                    task = await session.get(AsyncTaskRun, failure_task.id)
                    profile = await session.scalar(
                        select(CandidateProfile).where(CandidateProfile.resume_id == failure_resume_id)
                    )
                    assert resume is not None and resume.parse_status == "failed"
                    assert resume.failure_code == "schema_validation_failed"
                    assert task is not None and task.status == "failed"
                    assert task.failure_code == "schema_validation_failed"
                    assert task.finished_at is not None
                    assert profile is None
            finally:
                await database.close()

        asyncio.run(verify_terminal_states())
    finally:
        get_settings.cache_clear()


def test_object_cleanup_removes_only_expired_unreferenced_objects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database_url, redis_url = _require_integration_environment()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")

        async def verify_cleanup() -> None:
            database = create_database(database_url)
            storage = LocalObjectStorage(str(tmp_path / "objects"))
            old = datetime.now(UTC) - timedelta(hours=2)
            try:
                async with database.session_factory() as session:
                    user, candidate = await UserRepository(session).create_with_candidate(
                        username=f"cleanup-{uuid4()}",
                        password_hash="scrypt$integration-test-only",
                        name=None,
                    )
                    del user
                    unique_marker = uuid4().hex.encode()
                    orphan_upload = storage.put(b"orphan-" + unique_marker)
                    shared_upload = storage.put(b"shared-" + unique_marker)
                    job_upload = storage.put(b"job-shared-" + unique_marker)
                    async with session.begin():
                        orphan = StoredFileObject(
                            storage_key=orphan_upload.storage_key,
                            content_sha256=orphan_upload.content_sha256,
                            detected_mime_type="application/pdf",
                            file_size_bytes=orphan_upload.size_bytes,
                            status="ready",
                            created_at=old,
                            updated_at=old,
                        )
                        shared = StoredFileObject(
                            storage_key=shared_upload.storage_key,
                            content_sha256=shared_upload.content_sha256,
                            detected_mime_type="application/pdf",
                            file_size_bytes=shared_upload.size_bytes,
                            status="ready",
                            created_at=old,
                            updated_at=old,
                        )
                        job_shared = StoredFileObject(
                            storage_key=job_upload.storage_key,
                            content_sha256=job_upload.content_sha256,
                            detected_mime_type="text/markdown",
                            file_size_bytes=job_upload.size_bytes,
                            status="ready",
                            created_at=old,
                            updated_at=old,
                        )
                        session.add_all((orphan, shared, job_shared))
                        await session.flush()
                        session.add(
                            CandidateDocument(
                                candidate_id=candidate.id,
                                document_type="certificate",
                                document_name="shared.pdf",
                                file_type="pdf",
                                stored_file_object_id=shared.id,
                            )
                        )
                        hr_user = User(
                            username=f"cleanup-hr-{uuid4()}",
                            password_hash="scrypt$integration-test-only",
                        )
                        session.add(hr_user)
                        await session.flush()
                        hr_profile = HrProfile(user_id=hr_user.id)
                        session.add(hr_profile)
                        await session.flush()
                        session.add(
                            Job(
                                hr_profile_id=hr_profile.id,
                                stored_file_object_id=job_shared.id,
                            )
                        )
                    deleted = await ObjectCleanupService(
                        repository=ObjectStorageRepository(session), storage=storage
                    ).run_once()
                    assert deleted == 1
                    assert await session.get(StoredFileObject, orphan.id) is None
                    assert await session.get(StoredFileObject, shared.id) is not None
                    assert await session.get(StoredFileObject, job_shared.id) is not None
                    assert not (tmp_path / "objects" / orphan_upload.storage_key).exists()
                    assert (tmp_path / "objects" / shared_upload.storage_key).exists()
                    assert (tmp_path / "objects" / job_upload.storage_key).exists()
            finally:
                await database.close()

        asyncio.run(verify_cleanup())
    finally:
        get_settings.cache_clear()
