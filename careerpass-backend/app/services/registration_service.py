"""Application service for MVP Lite user registration."""

from __future__ import annotations

from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.repositories.user_repository import UsernameConflictError, UserRepository
from app.schemas.auth import AuthenticationResponse, RegisterRequest


class UsernameAlreadyExistsError(Exception):
    """Raised when registration cannot reserve the requested username."""


class RegistrationService:
    """Register a user without accessing the ORM session outside the Repository layer."""

    def __init__(self, *, user_repository: UserRepository, settings: Settings) -> None:
        self._user_repository = user_repository
        self._settings = settings

    async def register(self, request: RegisterRequest) -> AuthenticationResponse:
        """Atomically initialize a user and candidate, then issue a short-lived Access Token."""
        password_hash = hash_password(request.password.get_secret_value())
        try:
            identity = await self._user_repository.create_with_candidate(
                username=request.username,
                password_hash=password_hash,
                name=request.name,
            )
        except UsernameConflictError as exc:
            raise UsernameAlreadyExistsError from exc

        if identity is None:
            raise UsernameAlreadyExistsError

        user, candidate = identity
        access_token = create_access_token(user_id=user.id, settings=self._settings)
        return AuthenticationResponse(
            access_token=access_token,
            expires_in=self._settings.jwt_access_token_expire_minutes * 60,
            user={
                "user_id": user.id,
                "candidate_id": candidate.id,
                "profile_status": "incomplete",
            },
        )
