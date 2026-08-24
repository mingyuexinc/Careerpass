"""MVP Lite authenticated identity endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_login_service, get_registration_service
from app.core.config import get_settings
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.auth import (
    AuthenticationResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.response import success_response
from app.services.login_service import InvalidCredentialsError, LoginService
from app.services.registration_service import RegistrationService, UsernameAlreadyExistsError

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register")
async def register(
    payload: RegisterRequest,
    service: Annotated[RegistrationService, Depends(get_registration_service)],
) -> dict[str, object]:
    """Register an account and atomically initialize its Candidate identity."""
    if not get_settings().registration_enabled:
        raise AppException(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="registration is disabled",
        )
    try:
        response = await service.register(payload)
    except UsernameAlreadyExistsError:
        raise AppException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="username already exists",
        ) from None
    return _authentication_success(response)


@auth_router.post("/login")
async def login(
    payload: LoginRequest,
    service: Annotated[LoginService, Depends(get_login_service)],
) -> dict[str, object]:
    """Authenticate credentials and return an MVP Lite Access Token."""
    try:
        response = await service.login(payload)
    except InvalidCredentialsError:
        raise AppException(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            message="invalid credentials",
        ) from None
    return _authentication_success(response)


@auth_router.get("/me")
async def get_current_user(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
) -> dict[str, object]:
    """Return the minimum persisted identity for the authenticated request."""
    response = CurrentUserResponse(
        user_id=identity.user_id,
        roles=list(identity.roles),
        active_role=identity.active_role,
        candidate_id=identity.candidate_id,
        hr_profile_id=identity.hr_profile_id,
        username=identity.username,
        name=identity.name,
    )
    return success_response(response.model_dump(mode="json"))


def _authentication_success(response: AuthenticationResponse) -> dict[str, object]:
    """Wrap the intentional token-bearing response in the mandatory API envelope."""
    return success_response(response.model_dump(mode="json"))
