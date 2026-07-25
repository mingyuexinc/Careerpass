"""Application service for MVP Lite username and password login."""

from __future__ import annotations

from app.core.config import Settings
from app.core.security import create_access_token, verify_password
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthenticationResponse, LoginRequest


class InvalidCredentialsError(Exception):
    """Raised for every safe-to-report login authentication failure."""


class LoginService:
    """Authenticate an account and revalidate its unique candidate identity."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        candidate_repository: CandidateRepository,
        settings: Settings,
    ) -> None:
        self._user_repository = user_repository
        self._candidate_repository = candidate_repository
        self._settings = settings

    async def login(self, request: LoginRequest) -> AuthenticationResponse:
        """Issue an Access Token only after credentials and candidate ownership are verified."""
        user = await self._user_repository.get_by_username(request.username)
        password = request.password.get_secret_value()
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError

        candidate = await self._candidate_repository.get_by_user_id(user.id)
        if candidate is None or candidate.user_id != user.id:
            raise InvalidCredentialsError

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
