"""Controlled-demo account initialization service."""

from __future__ import annotations

from collections.abc import Iterable

from app.core.config import AppEnvironment, Settings, get_settings
from app.core.security import hash_password
from app.repositories.demo_account_repository import DemoAccount, DemoAccountRepository


def default_demo_accounts(settings: Settings | None = None) -> tuple[DemoAccount, DemoAccount]:
    """Return environment-specific controlled identities without production fallbacks."""
    settings = settings or get_settings()
    if settings.app_env is AppEnvironment.PRODUCTION:
        assert settings.demo_candidate_username is not None
        assert settings.demo_candidate_password is not None
        assert settings.demo_hr_username is not None
        assert settings.demo_hr_password is not None
        return (
            DemoAccount(
                username=settings.demo_candidate_username,
                password=settings.demo_candidate_password.get_secret_value(),
                role="candidate",
                name="Alex Chen",
            ),
            DemoAccount(
                username=settings.demo_hr_username,
                password=settings.demo_hr_password.get_secret_value(),
                role="hr",
                name="Mia Wang",
            ),
        )
    return (
        DemoAccount(
            username=settings.demo_candidate_username or "candidate_01",
            password=(
                settings.demo_candidate_password.get_secret_value()
                if settings.demo_candidate_password is not None
                else "123"
            ),
            role="candidate",
            name="Alex Chen",
        ),
        DemoAccount(
            username=settings.demo_hr_username or "hr_01",
            password=(
                settings.demo_hr_password.get_secret_value()
                if settings.demo_hr_password is not None
                else "123"
            ),
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
