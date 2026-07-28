"""Worker-facing execution lease service; parsing is intentionally a later task."""

from uuid import UUID

from app.repositories.async_task_repository import AsyncTaskRepository, ExecutionLease


class AsyncTaskExecutionService:
    """Acquire durable leases before a worker reads any candidate-owned resource."""

    def __init__(self, *, repository: AsyncTaskRepository, lease_seconds: int) -> None:
        self._repository = repository
        self._lease_seconds = lease_seconds

    async def claim(self, task_run_id: UUID) -> ExecutionLease | None:
        """Return one current lease or safely ignore duplicate/late broker delivery."""
        return await self._repository.claim_execution(
            task_run_id=task_run_id,
            lease_seconds=self._lease_seconds,
        )

    async def release_for_retry(self, lease: ExecutionLease) -> bool:
        """Release only the matching lease before a future worker retry is scheduled."""
        return await self._repository.release_execution_for_retry(
            task_run_id=lease.task_run_id,
            execution_token=lease.execution_token,
        )
