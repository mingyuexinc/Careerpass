"""Repository for idempotent controlled-demo account initialization."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_password
from app.infrastructure.database.models import Candidate, HrProfile, User, UserRole


@dataclass(frozen=True, slots=True)
class DemoAccount:
    username: str
    password: str
    role: str
    name: str


class DemoAccountRepository:
    """Create or reuse the fixed demo identities in one database transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_account(self, account: DemoAccount) -> None:
        async with self._session.begin():
            result = await self._session.execute(
                select(User)
                .options(selectinload(User.roles), selectinload(User.candidate), selectinload(User.hr_profile))
                .where(User.username == account.username)
            )
            user = result.scalar_one_or_none()
            if user is None:
                user = User(username=account.username, password_hash=account.password)
                user.roles = []
                user.candidate = None
                user.hr_profile = None
                self._session.add(user)
                await self._session.flush()
            elif not verify_password(account.password, user.password_hash):
                user.password_hash = account.password

            if not any(role.role == account.role for role in user.roles):
                self._session.add(UserRole(user=user, role=account.role))
            if account.role == "candidate":
                if user.candidate is None:
                    self._session.add(Candidate(user=user, name=account.name))
            elif account.role == "hr" and user.hr_profile is None:
                self._session.add(HrProfile(user=user, name=account.name))
            await self._session.flush()
