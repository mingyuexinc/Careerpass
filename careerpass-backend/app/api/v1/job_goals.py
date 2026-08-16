"""Authenticated candidate-owned S-06 current job-goal endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_job_goal_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.job_goal import JobGoalInput
from app.schemas.response import success_response
from app.services.job_goal_service import JobGoalLockedError, JobGoalService

job_goal_router = APIRouter(tags=["job-goals"])


def _candidate_id(identity: CurrentIdentity):
    if identity.active_role != "candidate" or identity.candidate_id is None:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="candidate identity required",
        )
    return identity.candidate_id


@job_goal_router.get("/job_goals/current")
async def get_current_job_goal(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[JobGoalService, Depends(get_job_goal_service)],
) -> dict[str, object]:
    value = await service.get_current(candidate_id=_candidate_id(identity))
    return success_response(value.model_dump(mode="json"))


@job_goal_router.put("/job_goals/current")
async def save_current_job_goal(
    value: JobGoalInput,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[JobGoalService, Depends(get_job_goal_service)],
) -> dict[str, object]:
    try:
        goal = await service.save_current(
            candidate_id=_candidate_id(identity),
            value=value,
        )
    except JobGoalLockedError:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.PRECONDITION_NOT_MET,
            message="job goal cannot be modified after Agent startup",
        ) from None
    return success_response(
        {"goal": goal.model_dump(mode="json")},
        msg="job goal saved",
    )
