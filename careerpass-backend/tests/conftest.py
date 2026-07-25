"""Shared test configuration for the backend."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-with-at-least-32-characters")

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def disable_auth_rate_limit_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit/API tests isolated unless a test explicitly enables Redis limiting."""
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create an application client with a clean settings cache."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()
