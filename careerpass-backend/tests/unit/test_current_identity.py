"""Tests for the unified current-identity dependency."""

import asyncio
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.api.dependencies import auth
from app.core.config import Settings
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.core.security import create_access_token
from app.infrastructure.database.models import User


class _SessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_: object) -> None:
        return None


class _Database:
    def session_factory(self) -> _SessionContext:
        return _SessionContext()


class _IdentityRepository:
    identity: CurrentIdentity | None = None

    def __init__(self, _: object) -> None:
        pass

    async def get_current(self, *, user_id: object, active_role: object = None) -> CurrentIdentity | None:
        return self.identity


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test",
        redis_url="redis://localhost:6379/15",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
        _env_file=None,
    )


def _request() -> Request:
    app = FastAPI()
    app.state.database = _Database()
    scope = {"type": "http", "method": "GET", "path": "/api/v1/auth/me", "app": app}
    return Request(cast(dict[str, object], scope))


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_current_identity_validates_token_and_persisted_ownership(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    user = User(id=uuid4(), username="alice", password_hash="scrypt$hash")
    identity = CurrentIdentity(
        user_id=user.id,
        username="alice",
        name="Alice",
        roles=("candidate",),
        active_role="candidate",
        candidate_id=uuid4(),
    )
    _IdentityRepository.identity = identity
    monkeypatch.setattr(auth, "IdentityRepository", _IdentityRepository)

    resolved = asyncio.run(
        auth.get_current_identity(
            request=_request(),
            credentials=_credentials(create_access_token(user_id=user.id, settings=settings)),
            settings=settings,
        )
    )

    assert resolved.user_id == user.id
    assert resolved.candidate_id == identity.candidate_id
    assert resolved.username == "alice"
    assert resolved.name == "Alice"


@pytest.mark.parametrize("credentials", [None, _credentials("not-a-jwt")])
def test_current_identity_rejects_missing_or_invalid_tokens(
    credentials: HTTPAuthorizationCredentials | None,
    settings: Settings,
) -> None:
    with pytest.raises(AppException) as error:
        asyncio.run(
            auth.get_current_identity(
                request=_request(),
                credentials=credentials,
                settings=settings,
            )
        )

    assert error.value.code is ErrorCode.UNAUTHORIZED
    assert error.value.message == "authentication failed"


def test_current_identity_rejects_a_token_for_a_missing_user(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    _IdentityRepository.identity = None
    monkeypatch.setattr(auth, "IdentityRepository", _IdentityRepository)

    with pytest.raises(AppException) as error:
        asyncio.run(
            auth.get_current_identity(
                request=_request(),
                credentials=_credentials(create_access_token(user_id=uuid4(), settings=settings)),
                settings=settings,
            )
        )

    assert error.value.code is ErrorCode.UNAUTHORIZED


def test_current_identity_rejects_missing_or_mismatched_identity(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    user = User(id=uuid4(), username="alice", password_hash="scrypt$hash")
    _IdentityRepository.identity = None
    monkeypatch.setattr(auth, "IdentityRepository", _IdentityRepository)

    with pytest.raises(AppException) as error:
        asyncio.run(
            auth.get_current_identity(
                request=_request(),
                credentials=_credentials(create_access_token(user_id=user.id, settings=settings)),
                settings=settings,
            )
        )

    assert error.value.code is ErrorCode.UNAUTHORIZED
