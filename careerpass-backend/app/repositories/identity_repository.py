"""Repository for resolving User role memberships and business identities."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.identity import CurrentIdentity, UserRole
from app.infrastructure.database.models import User


class IdentityRepository:
    """Resolve the current User and its selected role without exposing ORM sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(
        self,
        *,
        user_id: UUID,
        active_role: UserRole | None = None,
    ) -> CurrentIdentity | None:
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.roles), selectinload(User.candidate), selectinload(User.hr_profile))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None

        roles = tuple(sorted({role.role for role in user.roles}))
        if not roles:
            return None
        selected_role = active_role or (roles[0] if len(roles) == 1 else None)
        if selected_role is None or selected_role not in roles:
            return None
        if selected_role == "candidate" and (
            user.candidate is None or user.candidate.user_id != user.id
        ):
            return None
        if selected_role == "hr" and (
            user.hr_profile is None or user.hr_profile.user_id != user.id
        ):
            return None

        return CurrentIdentity(
            user_id=user.id,
            username=user.username,
            name=(user.candidate.name if selected_role == "candidate" and user.candidate else None)
            or (user.hr_profile.name if selected_role == "hr" and user.hr_profile else None),
            roles=roles,
            active_role=selected_role,
            candidate_id=user.candidate.id if user.candidate else None,
            hr_profile_id=user.hr_profile.id if user.hr_profile else None,
        )
