"""Candidate-facing S-08 application projection."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_application_service, get_matching_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.application import ApplicationStatusUpdateRequest
from app.schemas.response import success_response
from app.services.application_service import (
    ApplicationService,
    ApplicationStatusConflictError,
    HrApplicationNotFoundError,
)
from app.services.matching_service import MatchingService

applications_router = APIRouter(prefix="/applications", tags=["applications"])


def _candidate_id(identity: CurrentIdentity):
    if identity.active_role != "candidate" or identity.candidate_id is None:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="candidate access required")
    return identity.candidate_id


def _hr_profile_id(identity: CurrentIdentity) -> UUID:
    if identity.active_role != "hr" or identity.hr_profile_id is None:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="HR identity required")
    return identity.hr_profile_id


@applications_router.get("/current")
async def get_current_applications(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[MatchingService, Depends(get_matching_service)],
) -> dict[str, object]:
    result = await service.list_current_applications(candidate_id=_candidate_id(identity))
    data = {
        "run": result.run.model_dump(mode="json", exclude_none=True) if result.run else None,
        "applications": [item.model_dump(mode="json") for item in result.applications],
        "total": len(result.applications),
        "matching": result.summary.model_dump(mode="json"),
    }
    return success_response(data)


@applications_router.get("/hr/current")
async def get_current_hr_applications(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
) -> dict[str, object]:
    applications = await service.list_current_for_hr(hr_profile_id=_hr_profile_id(identity))
    return success_response(
        {
            "applications": [item.model_dump(mode="json") for item in applications],
            "total": len(applications),
        }
    )


@applications_router.patch("/{application_id}/status")
async def update_application_status(
    application_id: UUID,
    value: ApplicationStatusUpdateRequest,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
) -> dict[str, object]:
    try:
        application = await service.update_status(
            application_id=application_id,
            hr_profile_id=_hr_profile_id(identity),
            status=value.status,
        )
    except HrApplicationNotFoundError:
        raise AppException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="application not found",
        ) from None
    except ApplicationStatusConflictError:
        raise AppException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="application status transition is not allowed",
        ) from None
    return success_response(application.model_dump(mode="json"))
