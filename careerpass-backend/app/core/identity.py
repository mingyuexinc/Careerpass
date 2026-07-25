"""Trusted current-user identity passed from API authentication to business code."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CurrentIdentity:
    """A User and Candidate pair verified against the persisted ownership relation."""

    user_id: UUID
    candidate_id: UUID
    username: str
    name: str | None
