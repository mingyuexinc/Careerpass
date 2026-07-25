"""Tests for registration orchestration and its security boundaries."""

import asyncio
from typing import cast
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import decode_access_token, verify_password
from app.infrastructure.database.models import Candidate, User
from app.repositories.user_repository import UsernameConflictError, UserRepository
from app.schemas.auth import RegisterRequest
from app.services.registration_service import RegistrationService, UsernameAlreadyExistsError


class _RegisteringUserRepository:
    def __init__(self, result: tuple[User, Candidate] | None) -> None:
        self._result = result
        self.arguments: dict[str, str | None] | None = None

    async def create_with_candidate(
        self,
        *,
        username: str,
        password_hash: str,
        name: str | None,
    ) -> tuple[User, Candidate] | None:
        self.arguments = {
            "username": username,
            "password_hash": password_hash,
            "name": name,
        }
        return self._result


class _RacingUserRepository:
    async def create_with_candidate(self, **_: object) -> tuple[User, Candidate] | None:
        raise UsernameConflictError


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test",
        redis_url="redis://localhost:6379/15",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
        _env_file=None,
    )


def test_register_initializes_identity_and_issues_access_token(settings: Settings) -> None:
    user = User(id=uuid4(), username="alice", password_hash="unused")
    candidate = Candidate(id=uuid4(), user_id=user.id, name="Alice")
    repository = _RegisteringUserRepository((user, candidate))
    service = RegistrationService(
        user_repository=cast(UserRepository, repository),
        settings=settings,
    )

    response = asyncio.run(
        service.register(
            RegisterRequest(username="alice", password="StrongPassword123!", name="Alice")
        )
    )

    assert repository.arguments is not None
    assert repository.arguments["password_hash"] != "StrongPassword123!"
    assert verify_password("StrongPassword123!", str(repository.arguments["password_hash"]))
    assert decode_access_token(token=response.access_token, settings=settings) == user.id
    assert response.user.user_id == user.id
    assert response.user.candidate_id == candidate.id
    assert response.user.profile_status == "incomplete"
    assert response.expires_in == 1800


def test_register_rejects_existing_username_without_issuing_a_token(settings: Settings) -> None:
    repository = _RegisteringUserRepository(None)
    service = RegistrationService(
        user_repository=cast(UserRepository, repository),
        settings=settings,
    )

    with pytest.raises(UsernameAlreadyExistsError):
        asyncio.run(
            service.register(RegisterRequest(username="alice", password="StrongPassword123!"))
        )

    assert repository.arguments is not None


def test_register_maps_concurrent_username_conflict_to_domain_error(settings: Settings) -> None:
    service = RegistrationService(
        user_repository=cast(UserRepository, _RacingUserRepository()),
        settings=settings,
    )

    with pytest.raises(UsernameAlreadyExistsError):
        asyncio.run(
            service.register(RegisterRequest(username="alice", password="StrongPassword123!"))
        )
