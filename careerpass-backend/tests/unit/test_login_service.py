"""Tests for login authentication and candidate identity revalidation."""

import asyncio
from typing import cast
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import decode_access_token, hash_password
from app.infrastructure.database.models import Candidate, User
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest
from app.services.login_service import InvalidCredentialsError, LoginService


class _UserRepository:
    def __init__(self, user: User | None) -> None:
        self._user = user
        self.requested_username: str | None = None

    async def get_by_username(self, username: str) -> User | None:
        self.requested_username = username
        return self._user


class _CandidateRepository:
    def __init__(self, candidate: Candidate | None) -> None:
        self._candidate = candidate
        self.requested_user_id = None

    async def get_by_user_id(self, user_id: object) -> Candidate | None:
        self.requested_user_id = user_id
        return self._candidate


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test",
        redis_url="redis://localhost:6379/15",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
        _env_file=None,
    )


def _service(
    *,
    user: User | None,
    candidate: Candidate | None,
    settings: Settings,
) -> tuple[LoginService, _UserRepository, _CandidateRepository]:
    users = _UserRepository(user)
    candidates = _CandidateRepository(candidate)
    return (
        LoginService(
            user_repository=cast(UserRepository, users),
            candidate_repository=cast(CandidateRepository, candidates),
            settings=settings,
        ),
        users,
        candidates,
    )


def test_login_verifies_credentials_and_candidate_identity(settings: Settings) -> None:
    user = User(
        id=uuid4(),
        username="alice",
        password_hash=hash_password("StrongPassword123!"),
    )
    candidate = Candidate(id=uuid4(), user_id=user.id, name="Alice")
    service, users, candidates = _service(user=user, candidate=candidate, settings=settings)

    response = asyncio.run(
        service.login(LoginRequest(username="alice", password="StrongPassword123!"))
    )

    assert users.requested_username == "alice"
    assert candidates.requested_user_id == user.id
    assert decode_access_token(token=response.access_token, settings=settings) == user.id
    assert response.user.user_id == user.id
    assert response.user.candidate_id == candidate.id
    assert response.user.profile_status == "incomplete"
    assert response.expires_in == 1800


def test_login_hides_unknown_user_as_invalid_credentials(settings: Settings) -> None:
    service, _, candidates = _service(user=None, candidate=None, settings=settings)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.login(LoginRequest(username="alice", password="StrongPassword123!")))

    assert candidates.requested_user_id is None


def test_login_hides_wrong_password_as_invalid_credentials(settings: Settings) -> None:
    user = User(
        id=uuid4(),
        username="alice",
        password_hash=hash_password("StrongPassword123!"),
    )
    service, _, candidates = _service(user=user, candidate=None, settings=settings)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.login(LoginRequest(username="alice", password="WrongPassword123!")))

    assert candidates.requested_user_id is None


@pytest.mark.parametrize("candidate_user_id", [None, uuid4()])
def test_login_rejects_missing_or_mismatched_candidate(
    candidate_user_id: object,
    settings: Settings,
) -> None:
    user = User(
        id=uuid4(),
        username="alice",
        password_hash=hash_password("StrongPassword123!"),
    )
    candidate = (
        None
        if candidate_user_id is None
        else Candidate(id=uuid4(), user_id=candidate_user_id, name="Other")
    )
    service, _, _ = _service(user=user, candidate=candidate, settings=settings)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.login(LoginRequest(username="alice", password="StrongPassword123!")))
