"""Optional integration tests against isolated PostgreSQL and Redis services."""

import asyncio
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.infrastructure.database import create_database
from app.main import create_app
from app.repositories import CandidateRepository, UserRepository

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
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "true")
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "head")
        command.upgrade(config, "head")

        async def assert_identity_schema_and_repositories() -> None:
            database = create_database(database_url)
            try:
                async with database.session_factory() as session:
                    tables = await session.execute(
                        text("SELECT to_regclass('public.users'), to_regclass('public.candidates')")
                    )
                    assert tables.one() == ("users", "candidates")

                    triggers = await session.execute(
                        text(
                            """
                            SELECT tgname
                            FROM pg_trigger
                            WHERE tgname IN (
                                'trg_users_set_updated_at',
                                'trg_candidates_set_updated_at'
                            )
                            ORDER BY tgname
                            """
                        )
                    )
                    assert [row.tgname for row in triggers] == [
                        "trg_candidates_set_updated_at",
                        "trg_users_set_updated_at",
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
