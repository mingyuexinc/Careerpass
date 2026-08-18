"""S-08 synchronous orchestration after S-07 context commit."""

from __future__ import annotations

from uuid import UUID

from app.repositories.matching_repository import MatchingRepository
from app.services.matching_algorithm_v0_1 import ALGORITHM_VERSION, evaluate


class MatchingService:
    """Run one deterministic, idempotent matching round."""

    def __init__(self, *, repository: MatchingRepository) -> None:
        self._repository = repository

    async def execute(self, *, run_id: UUID, candidate_id: UUID) -> None:
        async with self._repository.transaction():
            inputs = await self._repository.load_run_input(
                run_id=run_id, candidate_id=candidate_id
            )
            if inputs is None or inputs.run.status != "running":
                return
            for job in inputs.jobs:
                existing = await self._repository.get_match(run_id=run_id, job_id=job.job_id)
                if existing is not None:
                    if existing.status == "matched":
                        await self._repository.ensure_application(match=existing)
                    continue
                result = evaluate(job=job, candidate=inputs.candidate, goal=inputs.goal)
                match = await self._repository.create_match(
                    run_id=run_id,
                    candidate_id=candidate_id,
                    job_id=job.job_id,
                    algorithm_version=ALGORITHM_VERSION,
                    result=result,
                )
                if result.status == "matched":
                    await self._repository.ensure_application(match=match)
            if await self._repository.count_applications(
                run_id=run_id, candidate_id=candidate_id
            ) == 0:
                await self._repository.finish_no_match(
                    run_id=run_id, candidate_id=candidate_id
                )

    async def list_current_applications(self, *, candidate_id: UUID):
        async with self._repository.transaction():
            return await self._repository.list_current_applications(candidate_id=candidate_id)
