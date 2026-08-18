"""S-07 Agent startup endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_agent_run_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.response import success_response
from app.services.agent_run_service import AgentRunPreconditionError, AgentRunService

agent_run_router = APIRouter(prefix="/agent_runs", tags=["agent-runs"])


def _candidate_id(identity: CurrentIdentity) -> UUID:
    if identity.active_role != "candidate" or identity.candidate_id is None:
        raise AppException(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="candidate access required",
        )
    return identity.candidate_id


@agent_run_router.get("/current")
async def get_current_agent_run(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[AgentRunService, Depends(get_agent_run_service)],
) -> dict[str, object]:
    value = await service.get_current(candidate_id=_candidate_id(identity))
    return success_response(value.model_dump(mode="json", exclude_none=True))


@agent_run_router.post("/current/start")
async def start_current_agent_run(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[AgentRunService, Depends(get_agent_run_service)],
) -> dict[str, object]:
    try:
        value = await service.start(candidate_id=_candidate_id(identity))
    except AgentRunPreconditionError:
        raise AppException(
            status_code=409,
            code=ErrorCode.PRECONDITION_NOT_MET,
            message="agent startup prerequisites are not met",
        ) from None
    return success_response(value.model_dump(mode="json"))
