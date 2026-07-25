"""Tests for local password hashing and Access Token primitives."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test",
        redis_url="redis://localhost:6379/15",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
        _env_file=None,
    )


def test_password_hash_is_salted_and_verifiable() -> None:
    first_hash = hash_password("StrongPassword123!")
    second_hash = hash_password("StrongPassword123!")

    assert first_hash != second_hash
    assert "StrongPassword123!" not in first_hash
    assert verify_password("StrongPassword123!", first_hash)
    assert not verify_password("WrongPassword123!", first_hash)


def test_access_token_round_trip(settings: Settings) -> None:
    user_id = uuid4()

    token = create_access_token(user_id=user_id, settings=settings)

    assert decode_access_token(token=token, settings=settings) == user_id


def test_access_token_rejects_expired_token(settings: Settings) -> None:
    token = create_access_token(
        user_id=uuid4(),
        settings=settings,
        now=datetime.now(UTC) - timedelta(minutes=31),
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token=token, settings=settings)


def test_access_token_rejects_a_token_signed_with_a_different_key(settings: Settings) -> None:
    token = create_access_token(user_id=uuid4(), settings=settings)
    other_settings = Settings(
        database_url="postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test",
        redis_url="redis://localhost:6379/15",
        jwt_secret_key="another-jwt-secret-key-with-at-least-32-chars",
        _env_file=None,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token=token, settings=other_settings)
