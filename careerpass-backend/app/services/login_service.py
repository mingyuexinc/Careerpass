"""Application service for MVP Lite username and password login."""

from __future__ import annotations

from app.core.config import Settings
from app.core.identity import CurrentIdentity
from app.core.security import create_access_token, verify_password
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthenticationResponse, LoginRequest


class InvalidCredentialsError(Exception):
    """Raised for every safe-to-report login authentication failure."""


class LoginService:
    """Authenticate an account and resolve its selected business identity."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        identity_repository: IdentityRepository,
        settings: Settings,
    ) -> None:
        self._user_repository = user_repository
        self._identity_repository = identity_repository
        self._settings = settings

    async def login(self, request: LoginRequest) -> AuthenticationResponse:
        """Issue an Access Token only after credentials and role identity are verified."""
        user = await self._user_repository.get_by_username(request.username)
        password = request.password.get_secret_value()
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError

        identity = await self._identity_repository.get_current(
            user_id=user.id,
            active_role=request.active_role,
        )
        if identity is None:
            raise InvalidCredentialsError

        access_token = create_access_token(
            user_id=user.id,
            settings=self._settings,
            active_role=identity.active_role,
        )
        return AuthenticationResponse(
            access_token=access_token,
            expires_in=self._settings.jwt_access_token_expire_minutes * 60,
            user=_identity_response(identity),
        )


def _identity_response(identity: CurrentIdentity) -> dict[str, object]:
    """Convert the trusted identity to the public minimum response."""
    current = identity
    return {
        "user_id": current.user_id,
        "roles": list(current.roles),
        "active_role": current.active_role,
        "candidate_id": current.candidate_id,
        "hr_profile_id": current.hr_profile_id,
    }
