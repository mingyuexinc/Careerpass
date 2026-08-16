"""Tests for L1 configuration safeguards."""

import pytest
from pydantic import ValidationError

from app.core.config import AppEnvironment, Settings


def test_settings_default_to_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = Settings(_env_file=None)

    assert settings.app_env is AppEnvironment.DEVELOPMENT
    assert settings.debug is False


def test_settings_reject_debug_in_production() -> None:
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings(app_env=AppEnvironment.PRODUCTION, debug=True, _env_file=None)


def test_settings_accept_production_without_debug() -> None:
    settings = Settings(
        app_env=AppEnvironment.PRODUCTION,
        debug=False,
        _env_file=None,
    )

    assert settings.app_env is AppEnvironment.PRODUCTION


def test_settings_reject_debug_reset_in_production() -> None:
    with pytest.raises(ValidationError, match="DEBUG_RESET_ENABLED"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            debug=False,
            debug_reset_enabled=True,
            _env_file=None,
        )

def test_settings_reject_invalid_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="preview", _env_file=None)


def test_settings_reject_blank_application_name() -> None:
    with pytest.raises(ValidationError):
        Settings(app_name="", _env_file=None)


def test_settings_reject_short_jwt_secret_key() -> None:
    with pytest.raises(ValidationError, match="jwt_secret_key"):
        Settings(jwt_secret_key="too-short", _env_file=None)


def test_settings_require_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_settings_require_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(ValidationError, match="redis_url"):
        Settings(_env_file=None)
