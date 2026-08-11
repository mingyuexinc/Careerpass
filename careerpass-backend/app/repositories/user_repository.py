"""Repository for user accounts and their atomic candidate initialization."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Candidate, User, UserRole


class UsernameConflictError(Exception):
    """Raised when the database rejects a duplicate username reservation."""


class UserRepository:
    """Own database access for accounts; callers never receive an ORM session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return an account by its primary key."""
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Return an account by its unique username."""
        result = await self._session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create_with_candidate(
        self,
        *,
        username: str,
        password_hash: str,
        name: str | None,
    ) -> tuple[User, Candidate] | None:
        """Create an account pair atomically, or return ``None`` when the username exists."""
        user = User(username=username, password_hash=password_hash)
        candidate = Candidate(user=user, name=name)
        try:
            async with self._session.begin():
                existing_user = await self._session.execute(
                    select(User.id).where(User.username == username)
                )
                if existing_user.scalar_one_or_none() is not None:
                    return None
                self._session.add_all((user, candidate, UserRole(user=user, role="candidate")))
                await self._session.flush()
        except IntegrityError as exc:
            if _is_username_conflict(exc):
                raise UsernameConflictError from exc
            raise
        return user, candidate


def _is_username_conflict(error: IntegrityError) -> bool:
    """Recognize the named unique constraint without leaking database details upward."""
    origin = error.orig
    constraint_name = getattr(origin, "constraint_name", None)
    if constraint_name is None:
        constraint_name = getattr(getattr(origin, "diag", None), "constraint_name", None)
    return constraint_name == "uq_user_username"
