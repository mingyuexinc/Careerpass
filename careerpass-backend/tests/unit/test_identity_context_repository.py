"""Tests for resolving the authenticated User and selected business identity."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from app.core.identity import CurrentIdentity
from app.infrastructure.database.models import Candidate, HrProfile, User, UserRole
from app.repositories.identity_repository import IdentityRepository

USER_ID = UUID("a2c51d36-f30d-4878-b38c-7951a97d1c2a")


def _user(*, candidate: bool = True, hr: bool = False) -> User:
    user = User(id=USER_ID, username="demo")
    user.roles = [
        UserRole(user_id=USER_ID, role=role)
        for role in (("candidate",) if candidate else ()) + (("hr",) if hr else ())
    ]
    user.candidate = Candidate(id=UUID("3911cbf8-7a30-4e3c-8e18-4afc4c3260bf"), user_id=USER_ID, name="Candidate") if candidate else None
    user.hr_profile = HrProfile(id=UUID("4a0e7ed4-0a70-42ba-9e4f-c893e4cbdc0a"), user_id=USER_ID, name="HR") if hr else None
    return user


def test_resolves_candidate_identity() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = _user()
    session.execute.return_value = result

    identity = asyncio.run(IdentityRepository(session).get_current(user_id=USER_ID))

    assert identity == CurrentIdentity(
        user_id=USER_ID,
        username="demo",
        name="Candidate",
        roles=("candidate",),
        active_role="candidate",
        candidate_id=UUID("3911cbf8-7a30-4e3c-8e18-4afc4c3260bf"),
    )


def test_requires_explicit_role_for_multi_role_identity() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = _user(hr=True)
    session.execute.return_value = result
    repository = IdentityRepository(session)

    assert asyncio.run(repository.get_current(user_id=USER_ID)) is None
    identity = asyncio.run(repository.get_current(user_id=USER_ID, active_role="hr"))

    assert identity is not None
    assert identity.active_role == "hr"
    assert identity.hr_profile_id == UUID("4a0e7ed4-0a70-42ba-9e4f-c893e4cbdc0a")


def test_rejects_unknown_user_or_missing_role_identity() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    result = MagicMock()
    session.execute.return_value = result
    repository = IdentityRepository(session)

    result.scalar_one_or_none.return_value = None
    assert asyncio.run(repository.get_current(user_id=USER_ID)) is None

    user = _user(candidate=False)
    result.scalar_one_or_none.return_value = user
    assert asyncio.run(repository.get_current(user_id=USER_ID)) is None

    user = _user(candidate=False, hr=True)
    assert asyncio.run(repository.get_current(user_id=USER_ID, active_role="candidate")) is None
