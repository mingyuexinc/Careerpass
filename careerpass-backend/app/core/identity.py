"""Trusted current-user identity passed from API authentication to business code."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

UserRole = Literal["candidate", "hr"]


@dataclass(frozen=True, slots=True)
class CurrentIdentity:
    """A User and selected business identity verified from persisted role data."""

    user_id: UUID
    username: str
    name: str | None
    roles: tuple[UserRole, ...]
    active_role: UserRole
    candidate_id: UUID | None = None
    hr_profile_id: UUID | None = None
