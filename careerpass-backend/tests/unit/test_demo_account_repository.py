"""Tests for repository-level demo account upsert behavior."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.infrastructure.database.models import Candidate, User, UserRole
from app.repositories.demo_account_repository import DemoAccount, DemoAccountRepository


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


def test_creates_candidate_account_and_role_in_one_transaction() -> None:
    session = SimpleNamespace(
        begin=lambda: _Transaction(),
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)),
        add=SimpleNamespace(),
        flush=AsyncMock(),
    )
    added = []
    session.add = added.append

    asyncio.run(
        DemoAccountRepository(session).ensure_account(
            DemoAccount(username="candidate_01", password="hashed", role="candidate", name="Alex Chen")
        )
    )

    assert any(isinstance(item, User) and item.username == "candidate_01" for item in added)
    assert any(isinstance(item, UserRole) and item.role == "candidate" for item in added)
    assert any(isinstance(item, Candidate) and item.name == "Alex Chen" for item in added)
    assert session.flush.await_count == 2
