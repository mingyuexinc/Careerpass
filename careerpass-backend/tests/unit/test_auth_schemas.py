"""Tests for authentication Pydantic contracts."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    AuthenticationResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)


def test_register_request_accepts_valid_credentials() -> None:
    request = RegisterRequest(username="alice.test", password="StrongPassword123!", name=" Alice ")

    assert request.username == "alice.test"
    assert request.password.get_secret_value() == "StrongPassword123!"
    assert request.name == "Alice"
    assert "StrongPassword123!" not in repr(request)


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("ab", "StrongPassword123!"),
        ("alice name", "StrongPassword123!"),
        ("alice", "nouppercase123!"),
        ("alice", "NOLOWERCASE123!"),
        ("alice", "NoDigitsPassword!"),
        ("alice", "NoSpecialPassword123"),
    ],
)
def test_credentials_reject_invalid_values(username: str, password: str) -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username=username, password=password)


def test_authentication_response_excludes_refresh_token() -> None:
    response = AuthenticationResponse(
        access_token="access-token",
        expires_in=1800,
        user={
            "user_id": uuid4(),
            "candidate_id": uuid4(),
            "profile_status": "incomplete",
        },
    )

    assert response.model_dump() == {
        "access_token": "access-token",
        "token_type": "Bearer",
        "expires_in": 1800,
        "user": response.user.model_dump(),
    }


def test_current_user_response_rejects_non_mvp_profile_status() -> None:
    with pytest.raises(ValidationError):
        CurrentUserResponse(
            user_id=uuid4(),
            candidate_id=uuid4(),
            profile_status="pending",
            username="alice",
        )
