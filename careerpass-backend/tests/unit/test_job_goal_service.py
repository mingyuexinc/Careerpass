import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.infrastructure.database.models import JobGoal
from app.schemas.job_goal import JobGoalInput
from app.services.job_goal_service import JobGoalLockedError, JobGoalService


class FakeJobGoalRepository:
    def __init__(self, goal: JobGoal | None, locked: bool = False) -> None:
        self.goal = goal
        self.locked = locked
        self.save_called = False

    @asynccontextmanager
    async def transaction(self):
        yield

    async def get_current(self, *, candidate_id):
        return self.goal

    async def has_locked_run(self, *, candidate_id):
        return self.locked

    async def save_current(self, **kwargs):
        self.save_called = True
        raise AssertionError("locked goals must not be persisted")


def test_service_rejects_non_active_goal_updates() -> None:
    goal = JobGoal(
        id=uuid4(),
        candidate_id=uuid4(),
        offer_target=1,
        title="后端开发",
        filters="",
        status="achieved",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    repository = FakeJobGoalRepository(goal)

    with pytest.raises(JobGoalLockedError):
        asyncio.run(
            JobGoalService(repository=repository).save_current(
                candidate_id=goal.candidate_id,
                value=JobGoalInput(offer_target=2, title="全栈开发", filters=""),
            )
        )

    assert repository.save_called is False


def test_service_rejects_updates_after_agent_run_is_created() -> None:
    goal = JobGoal(
        id=uuid4(),
        candidate_id=uuid4(),
        offer_target=1,
        title="后端开发",
        filters="",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    repository = FakeJobGoalRepository(goal, locked=True)

    with pytest.raises(JobGoalLockedError):
        asyncio.run(
            JobGoalService(repository=repository).save_current(
                candidate_id=goal.candidate_id,
                value=JobGoalInput(offer_target=2, title="全栈开发", filters=""),
            )
        )

    assert repository.save_called is False
