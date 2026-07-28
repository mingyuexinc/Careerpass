"""Unit tests for the reference-safe object cleanup control flow."""

import asyncio
from uuid import uuid4

import pytest

from app.infrastructure.storage.cleanup import (
    run_cleanup_schedule,
    run_hourly_object_cleanup,
    stop_cleanup_schedule,
)
from app.repositories.object_storage_repository import CleanupClaim
from app.services.object_cleanup_service import ObjectCleanupService


def test_cleanup_restores_status_after_physical_delete_failure() -> None:
    claim = CleanupClaim(object_id=uuid4(), storage_key="a" * 32, previous_status="ready")

    class Repository:
        restored: list[CleanupClaim] = []

        async def claim_expired_unreferenced(self, **_: object) -> list[CleanupClaim]:
            return [claim]

        async def restore_after_delete_failure(self, value: CleanupClaim) -> None:
            self.restored.append(value)

        async def finalize_deletion(self, _: object) -> bool:
            raise AssertionError("must not finalize after a storage failure")

    class Storage:
        def delete(self, _: str) -> None:
            raise OSError("simulated storage failure")

    repository = Repository()
    result = asyncio.run(ObjectCleanupService(repository=repository, storage=Storage()).run_once())  # type: ignore[arg-type]

    assert result == 0
    assert repository.restored == [claim]


def test_cleanup_rejects_invalid_batch_size() -> None:
    with pytest.raises(ValueError):
        asyncio.run(
            ObjectCleanupService(repository=object(), storage=object()).run_once(batch_size=0)
        )  # type: ignore[arg-type]


def test_cleanup_finalizes_successful_physical_deletion() -> None:
    claim = CleanupClaim(object_id=uuid4(), storage_key="b" * 32, previous_status="writing")

    class Repository:
        async def claim_expired_unreferenced(self, **_: object) -> list[CleanupClaim]:
            return [claim]

        async def restore_after_delete_failure(self, _: CleanupClaim) -> None:
            raise AssertionError("must not restore a successful deletion")

        async def finalize_deletion(self, _: object) -> bool:
            return True

    class Storage:
        deleted: list[str] = []

        def delete(self, storage_key: str) -> None:
            self.deleted.append(storage_key)

    storage = Storage()
    assert (
        asyncio.run(ObjectCleanupService(repository=Repository(), storage=storage).run_once()) == 1
    )  # type: ignore[arg-type]
    assert storage.deleted == [claim.storage_key]


def test_hourly_entrypoint_uses_a_fresh_repository_session(tmp_path) -> None:
    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    class Database:
        def session_factory(self) -> Session:
            return Session()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(ObjectCleanupService, "run_once", lambda _: asyncio.sleep(0, result=0))
        assert asyncio.run(run_hourly_object_cleanup(Database(), storage=object())) == 0  # type: ignore[arg-type]


def test_cleanup_schedule_runs_then_can_be_cancelled() -> None:
    calls: list[int] = []

    async def cleanup() -> int:
        calls.append(1)
        return 1

    async def execute() -> None:
        task = asyncio.create_task(run_cleanup_schedule(cleanup, interval_seconds=0))
        while not calls:
            await asyncio.sleep(0)
        await stop_cleanup_schedule(task)

    asyncio.run(execute())
    assert calls == [1]
