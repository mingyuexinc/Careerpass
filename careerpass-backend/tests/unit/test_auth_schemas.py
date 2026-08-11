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
    request = RegisterRequest(username="alice.test", password="weak", name=" Alice ")

    assert request.username == "alice.test"
    assert request.password.get_secret_value() == "weak"
    assert request.name == "Alice"
    assert "weak" not in repr(request)


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("ab", "StrongPassword123!"),
        ("alice name", "StrongPassword123!"),
        ("alice", ""),
        ("alice", "x" * 129),
    ],
)
def test_credentials_reject_invalid_values(username: str, password: str) -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username=username, password=password)


@pytest.mark.parametrize("password", ["letters", "123456", "!!!"])
def test_credentials_accept_nonempty_password_without_complexity_rules(password: str) -> None:
    request = LoginRequest(username="alice", password=password)

    assert request.password.get_secret_value() == password


def test_authentication_response_excludes_refresh_token() -> None:
    response = AuthenticationResponse(
        access_token="access-token",
        expires_in=1800,
        user={
            "user_id": uuid4(),
            "roles": ["candidate"],
            "active_role": "candidate",
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
            roles=["candidate"],
            active_role="candidate",
            candidate_id=uuid4(),
            profile_status="pending",
            username="alice",
        )
