"""Tests for controlled demo account initialization."""

import asyncio
from unittest.mock import AsyncMock

from app.core.security import verify_password
from app.repositories.demo_account_repository import DemoAccount
from app.services.demo_account_service import DemoAccountService


def test_demo_account_service_hashes_configured_passwords() -> None:
    repository = AsyncMock()
    service = DemoAccountService(repository)

    asyncio.run(
        service.ensure_accounts(
            [DemoAccount(username="candidate_01", password="123", role="candidate", name="Alex Chen")]
        )
    )

    account = repository.ensure_account.await_args.args[0]
    assert account.username == "candidate_01"
    assert account.role == "candidate"
    assert account.password != "123"
    assert verify_password("123", account.password)
