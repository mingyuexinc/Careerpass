"""Authenticated development reset endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_debug_reset_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.response import success_response
from app.services.debug_reset_service import (
    DebugResetDisabledError,
    DebugResetService,
    ResetAccountBusyError,
    ResetAccountConflictError,
)

debug_reset_router = APIRouter(prefix="/debug", tags=["debug"])


@debug_reset_router.post("/reset/current-account")
async def reset_current_account(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[DebugResetService, Depends(get_debug_reset_service)],
) -> dict[str, object]:
    try:
        await service.reset_current_account(identity)
    except DebugResetDisabledError:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="debug reset is disabled",
        ) from None
    except ResetAccountBusyError:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="reset is unavailable while account tasks are running",
        ) from None
    except ResetAccountConflictError:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="account reset is blocked by dependent data",
        ) from None
    return success_response(
        {"reset": True, "scope": "current_account"},
        msg="debug data reset",
    )
