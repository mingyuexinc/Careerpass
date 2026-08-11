"""Tests for login authentication and candidate identity revalidation."""

import asyncio
from typing import cast
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.identity import CurrentIdentity
from app.core.security import decode_access_token, hash_password
from app.infrastructure.database.models import User
from app.repositories.identity_repository import IdentityRepository
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


class _IdentityRepository:
    def __init__(self, identity: CurrentIdentity | None) -> None:
        self._identity = identity
        self.requested_user_id = None
        self.requested_role = None

    async def get_current(self, *, user_id: object, active_role: object = None) -> CurrentIdentity | None:
        self.requested_user_id = user_id
        self.requested_role = active_role
        return self._identity


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
    identity: CurrentIdentity | None,
    settings: Settings,
) -> tuple[LoginService, _UserRepository, _IdentityRepository]:
    users = _UserRepository(user)
    identities = _IdentityRepository(identity)
    return (
        LoginService(
            user_repository=cast(UserRepository, users),
            identity_repository=cast(IdentityRepository, identities),
            settings=settings,
        ),
        users,
        identities,
    )


def test_login_verifies_credentials_and_candidate_identity(settings: Settings) -> None:
    user = User(
        id=uuid4(),
        username="alice",
        password_hash=hash_password("StrongPassword123!"),
    )
    identity = CurrentIdentity(
        user_id=user.id,
        username="alice",
        name="Alice",
        roles=("candidate",),
        active_role="candidate",
        candidate_id=uuid4(),
    )
    service, users, identities = _service(user=user, identity=identity, settings=settings)

    response = asyncio.run(
        service.login(LoginRequest(username="alice", password="StrongPassword123!"))
    )

    assert users.requested_username == "alice"
    assert identities.requested_user_id == user.id
    assert identities.requested_role is None
    assert decode_access_token(token=response.access_token, settings=settings) == user.id
    assert response.user.user_id == user.id
    assert response.user.candidate_id == identity.candidate_id
    assert response.user.active_role == "candidate"
    assert response.expires_in == 1800


def test_login_hides_unknown_user_as_invalid_credentials(settings: Settings) -> None:
    service, _, identities = _service(user=None, identity=None, settings=settings)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.login(LoginRequest(username="alice", password="StrongPassword123!")))

    assert identities.requested_user_id is None


def test_login_hides_wrong_password_as_invalid_credentials(settings: Settings) -> None:
    user = User(
        id=uuid4(),
        username="alice",
        password_hash=hash_password("StrongPassword123!"),
    )
    service, _, identities = _service(user=user, identity=None, settings=settings)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.login(LoginRequest(username="alice", password="WrongPassword123!")))

    assert identities.requested_user_id is None


def test_login_rejects_missing_or_mismatched_identity(settings: Settings) -> None:
    user = User(
        id=uuid4(),
        username="alice",
        password_hash=hash_password("StrongPassword123!"),
    )
    service, _, _ = _service(user=user, identity=None, settings=settings)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.login(LoginRequest(username="alice", password="StrongPassword123!")))
