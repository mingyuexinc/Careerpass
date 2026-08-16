"""Unit tests for current-account reset orchestration."""

import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from app.core.identity import CurrentIdentity
from app.repositories.debug_reset_repository import ResetResources
from app.repositories.object_storage_repository import CleanupClaim
from app.services.debug_reset_service import (
    DebugResetDisabledError,
    DebugResetService,
)


def _identity() -> CurrentIdentity:
    return CurrentIdentity(
        user_id=uuid4(),
        username="candidate-demo",
        name="Demo Candidate",
        roles=("candidate",),
        active_role="candidate",
        candidate_id=uuid4(),
    )


class FakeRepository:
    def __init__(self, resources: ResetResources) -> None:
        self.resources = resources
        self.called = False

    @asynccontextmanager
    async def transaction(self):
        yield

    async def reset_current_account(self, identity: CurrentIdentity) -> ResetResources:
        self.called = True
        return self.resources


class FakeObjectRepository:
    def __init__(self) -> None:
        self.finalized: list[object] = []

    async def finalize_deletion(self, object_id: object) -> bool:
        self.finalized.append(object_id)
        return True


class FakeStorage:
    def __init__(self, fail: bool = False) -> None:
        self.deleted: list[str] = []
        self.fail = fail

    def delete(self, storage_key: str) -> None:
        if self.fail:
            raise OSError("storage unavailable")
        self.deleted.append(storage_key)


def test_reset_service_deletes_claimed_objects_after_transaction() -> None:
    claim = CleanupClaim(uuid4(), "a" * 32, "deleting")
    repository = FakeRepository(ResetResources((claim,)))
    objects = FakeObjectRepository()
    storage = FakeStorage()
    service = DebugResetService(
        repository=repository,
        object_repository=objects,
        storage=storage,
        enabled=True,
    )

    asyncio.run(service.reset_current_account(_identity()))

    assert repository.called is True
    assert storage.deleted == [claim.storage_key]
    assert objects.finalized == [claim.object_id]


def test_reset_service_keeps_retryable_cleanup_when_storage_fails() -> None:
    claim = CleanupClaim(uuid4(), "b" * 32, "deleting")
    objects = FakeObjectRepository()
    storage = FakeStorage(fail=True)
    service = DebugResetService(
        repository=FakeRepository(ResetResources((claim,))),
        object_repository=objects,
        storage=storage,
        enabled=True,
    )

    asyncio.run(service.reset_current_account(_identity()))

    assert objects.finalized == []


def test_reset_service_fails_closed_when_disabled() -> None:
    repository = FakeRepository(ResetResources(()))
    service = DebugResetService(
        repository=repository,
        object_repository=FakeObjectRepository(),
        storage=FakeStorage(),
        enabled=False,
    )

    with pytest.raises(DebugResetDisabledError):
        asyncio.run(service.reset_current_account(_identity()))
    assert repository.called is False
