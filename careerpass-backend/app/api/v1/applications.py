"""Candidate-facing S-08 application projection."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_matching_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.response import success_response
from app.services.matching_service import MatchingService

applications_router = APIRouter(prefix="/applications", tags=["applications"])


def _candidate_id(identity: CurrentIdentity):
    if identity.active_role != "candidate" or identity.candidate_id is None:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="candidate access required")
    return identity.candidate_id


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
    }
    return success_response(data)
