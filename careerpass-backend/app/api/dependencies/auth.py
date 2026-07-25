"""Bearer Access Token dependency with database-backed identity revalidation."""

from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.core.security import InvalidAccessTokenError, decode_access_token
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.user_repository import UserRepository

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentIdentity:
    """Validate a Bearer token and resolve its current User/Candidate ownership pair."""
    if credentials is None:
        raise _authentication_failed()

    try:
        user_id = decode_access_token(token=credentials.credentials, settings=settings)
    except InvalidAccessTokenError:
        raise _authentication_failed() from None

    database = request.app.state.database
    async with database.session_factory() as session:
        user = await UserRepository(session).get_by_id(user_id)
        if user is None:
            raise _authentication_failed()

        candidate = await CandidateRepository(session).get_by_user_id(user.id)
        if candidate is None or candidate.user_id != user.id:
            raise _authentication_failed()

    return CurrentIdentity(
        user_id=user.id,
        candidate_id=candidate.id,
        username=user.username,
        name=candidate.name,
    )


def _authentication_failed() -> AppException:
    return AppException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code=ErrorCode.UNAUTHORIZED,
        message="authentication failed",
    )
