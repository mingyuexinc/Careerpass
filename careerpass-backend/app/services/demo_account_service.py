"""Controlled-demo account initialization service."""

from __future__ import annotations

import os
from collections.abc import Iterable

from app.core.security import hash_password
from app.repositories.demo_account_repository import DemoAccount, DemoAccountRepository


def default_demo_accounts() -> tuple[DemoAccount, DemoAccount]:
    """Return the two controlled identities required by the demonstration."""
    return (
        DemoAccount(
            username="candidate_01",
            password=os.environ.get("DEMO_CANDIDATE_PASSWORD", "123"),
            role="candidate",
            name="Alex Chen",
        ),
        DemoAccount(
            username="hr_01",
            password=os.environ.get("DEMO_HR_PASSWORD", "123"),
            role="hr",
            name="Mia Wang",
        ),
    )


class DemoAccountService:
    """Initialize the two documented demo accounts without exposing registration."""

    def __init__(self, repository: DemoAccountRepository) -> None:
        self._repository = repository

    async def ensure_accounts(self, accounts: Iterable[DemoAccount]) -> None:
        for account in accounts:
            await self._repository.ensure_account(
                DemoAccount(
                    username=account.username,
                    password=hash_password(account.password),
                    role=account.role,
                    name=account.name,
                )
            )
