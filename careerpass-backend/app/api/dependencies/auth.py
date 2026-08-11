"""Bearer Access Token dependency with database-backed identity revalidation."""

from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.core.security import InvalidAccessTokenError, decode_access_token_context
from app.repositories.identity_repository import IdentityRepository

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentIdentity:
    """Validate a Bearer token and resolve its current User/role identity pair."""
    if credentials is None:
        raise _authentication_failed()

    try:
        user_id, active_role = decode_access_token_context(
            token=credentials.credentials,
            settings=settings,
        )
    except InvalidAccessTokenError:
        raise _authentication_failed() from None

    database = request.app.state.database
    async with database.session_factory() as session:
        identity = await IdentityRepository(session).get_current(
            user_id=user_id,
            active_role=active_role,
        )
        if identity is None:
            raise _authentication_failed()
    return identity


def _authentication_failed() -> AppException:
    return AppException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code=ErrorCode.UNAUTHORIZED,
        message="authentication failed",
    )
