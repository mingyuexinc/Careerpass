"""Unit coverage for the S-07 startup boundary."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.repositories.agent_run_repository import StartPreconditions
from app.schemas.agent_run import AgentRunStatusResponse
from app.services.agent_run_service import AgentRunPreconditionError, AgentRunService


def _goal():
    return SimpleNamespace(
        id=uuid4(),
        offer_target=2,
        title="前端工程师",
        filters="深圳",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _run():
    return SimpleNamespace(
        id=uuid4(), status="running", started_at=datetime.now(timezone.utc)
    )


class FakeAgentRunRepository:
    def __init__(self, conditions: StartPreconditions):
        self.conditions = conditions
        self.created = None

    @asynccontextmanager
    async def transaction(self):
        yield

    async def get_start_preconditions(self, *, candidate_id):
        return self.conditions

    async def create_running(self, **kwargs):
        self.created = kwargs
        return _run()


def _startable_conditions():
    goal = _goal()
    resume = SimpleNamespace(parse_status="succeeded", id=uuid4())
    profile = SimpleNamespace(id=uuid4(), matching_readiness="matching_ready")
    return StartPreconditions(goal, resume, 1, profile, None)


def test_start_creates_only_one_running_context() -> None:
    repository = FakeAgentRunRepository(_startable_conditions())
    service = AgentRunService(repository=repository)

    first = asyncio.run(service.start(candidate_id=uuid4()))
    assert first.run.status == "running"
    assert repository.created is not None
    assert "goal_snapshot" in repository.created


def test_duplicate_start_returns_existing_context() -> None:
    existing = _run()
    conditions = _startable_conditions()
    repository = FakeAgentRunRepository(
        StartPreconditions(conditions.goal, conditions.resume, 1, conditions.profile, existing)
    )
    value = asyncio.run(AgentRunService(repository=repository).start(candidate_id=uuid4()))
    assert value.run.id == existing.id
    assert repository.created is None


def test_unready_profile_cannot_start() -> None:
    conditions = _startable_conditions()
    conditions = StartPreconditions(
        conditions.goal,
        conditions.resume,
        conditions.resume_count,
        SimpleNamespace(id=uuid4(), matching_readiness="matching_not_ready"),
        None,
    )
    with pytest.raises(AgentRunPreconditionError):
        asyncio.run(AgentRunService(repository=FakeAgentRunRepository(conditions)).start(candidate_id=uuid4()))


def test_current_status_exposes_only_safe_projection() -> None:
    conditions = _startable_conditions()
    value = asyncio.run(AgentRunService(repository=FakeAgentRunRepository(conditions)).get_current(candidate_id=uuid4()))
    assert isinstance(value, AgentRunStatusResponse)
    assert value.state == "not_started"
    assert value.can_start is True
