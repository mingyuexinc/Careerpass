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
from app.core.security import create_access_token
from app.infrastructure.database.models import Candidate, User


class _SessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_: object) -> None:
        return None


class _Database:
    def session_factory(self) -> _SessionContext:
        return _SessionContext()


class _UserRepository:
    user: User | None = None

    def __init__(self, _: object) -> None:
        pass

    async def get_by_id(self, _: object) -> User | None:
        return self.user


class _CandidateRepository:
    candidate: Candidate | None = None

    def __init__(self, _: object) -> None:
        pass

    async def get_by_user_id(self, _: object) -> Candidate | None:
        return self.candidate


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
    candidate = Candidate(id=uuid4(), user_id=user.id, name="Alice")
    _UserRepository.user = user
    _CandidateRepository.candidate = candidate
    monkeypatch.setattr(auth, "UserRepository", _UserRepository)
    monkeypatch.setattr(auth, "CandidateRepository", _CandidateRepository)

    identity = asyncio.run(
        auth.get_current_identity(
            request=_request(),
            credentials=_credentials(create_access_token(user_id=user.id, settings=settings)),
            settings=settings,
        )
    )

    assert identity.user_id == user.id
    assert identity.candidate_id == candidate.id
    assert identity.username == "alice"
    assert identity.name == "Alice"


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
    _UserRepository.user = None
    monkeypatch.setattr(auth, "UserRepository", _UserRepository)

    with pytest.raises(AppException) as error:
        asyncio.run(
            auth.get_current_identity(
                request=_request(),
                credentials=_credentials(create_access_token(user_id=uuid4(), settings=settings)),
                settings=settings,
            )
        )

    assert error.value.code is ErrorCode.UNAUTHORIZED


@pytest.mark.parametrize("candidate_user_id", [None, uuid4()])
def test_current_identity_rejects_missing_or_mismatched_candidate(
    monkeypatch: pytest.MonkeyPatch,
    candidate_user_id: object,
    settings: Settings,
) -> None:
    user = User(id=uuid4(), username="alice", password_hash="scrypt$hash")
    _UserRepository.user = user
    _CandidateRepository.candidate = (
        None
        if candidate_user_id is None
        else Candidate(id=uuid4(), user_id=candidate_user_id, name="Other")
    )
    monkeypatch.setattr(auth, "UserRepository", _UserRepository)
    monkeypatch.setattr(auth, "CandidateRepository", _CandidateRepository)

    with pytest.raises(AppException) as error:
        asyncio.run(
            auth.get_current_identity(
                request=_request(),
                credentials=_credentials(create_access_token(user_id=user.id, settings=settings)),
                settings=settings,
            )
        )

    assert error.value.code is ErrorCode.UNAUTHORIZED
