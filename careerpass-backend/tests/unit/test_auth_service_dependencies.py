"""Tests for API dependency assembly of authentication application services."""

import asyncio
from typing import cast

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from app.api.dependencies.services import get_login_service, get_registration_service
from app.core.config import Settings
from app.services.login_service import LoginService
from app.services.registration_service import RegistrationService


class _SessionContext:
    def __init__(self) -> None:
        self.closed = False

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_: object) -> None:
        self.closed = True


class _Database:
    def __init__(self) -> None:
        self.contexts: list[_SessionContext] = []

    def session_factory(self) -> _SessionContext:
        context = _SessionContext()
        self.contexts.append(context)
        return context


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test",
        redis_url="redis://localhost:6379/15",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
        _env_file=None,
    )


def _request(database: _Database) -> Request:
    app = FastAPI()
    app.state.database = database
    return Request(cast(dict[str, object], {"type": "http", "app": app}))


def test_auth_service_dependencies_close_their_repository_sessions(settings: Settings) -> None:
    database = _Database()

    async def resolve_services() -> tuple[RegistrationService, LoginService]:
        registration_dependency = get_registration_service(_request(database), settings)
        login_dependency = get_login_service(_request(database), settings)
        registration_service = await anext(registration_dependency)
        login_service = await anext(login_dependency)
        await registration_dependency.aclose()
        await login_dependency.aclose()
        return registration_service, login_service

    registration_service, login_service = asyncio.run(resolve_services())

    assert isinstance(registration_service, RegistrationService)
    assert isinstance(login_service, LoginService)
    assert len(database.contexts) == 2
    assert all(context.closed for context in database.contexts)
