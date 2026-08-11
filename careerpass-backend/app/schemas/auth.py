"""Pydantic contracts for MVP Lite authentication endpoints."""

from __future__ import annotations

import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

Username = Annotated[str, Field(min_length=3, max_length=64)]
CandidateName = Annotated[str, Field(min_length=1, max_length=64)]
ProfileStatus = Literal["incomplete", "blocked", "ready"]
UserRole = Literal["candidate", "hr"]


class _AuthenticationRequest(BaseModel):
    """Shared validation for credential-bearing inputs."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: Username
    password: SecretStr = Field(min_length=1, max_length=128, repr=False)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not _USERNAME_PATTERN.fullmatch(value):
            raise ValueError("username contains unsupported characters")
        return value


class RegisterRequest(_AuthenticationRequest):
    """Input accepted by ``POST /api/v1/auth/register``."""

    name: CandidateName | None = None


class LoginRequest(_AuthenticationRequest):
    """Input accepted by ``POST /api/v1/auth/login``."""

    active_role: UserRole | None = None


class AuthenticatedUser(BaseModel):
    """Minimum identity returned after successful registration or login."""

    user_id: UUID
    roles: list[UserRole]
    active_role: UserRole
    candidate_id: UUID | None = None
    hr_profile_id: UUID | None = None
    profile_status: ProfileStatus | None = None


class AuthenticationResponse(BaseModel):
    """MVP Lite session response; Refresh Token fields are deliberately absent."""

    access_token: str = Field(min_length=1, repr=False)
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(gt=0)
    user: AuthenticatedUser


class CurrentUserResponse(AuthenticatedUser):
    """Minimum identity returned by ``GET /api/v1/auth/me``."""

    username: Username
    name: CandidateName | None = None
