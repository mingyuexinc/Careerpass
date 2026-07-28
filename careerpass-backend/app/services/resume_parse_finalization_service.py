"""Lease-guarded terminal state orchestration for one resume parsing execution."""

from app.repositories.async_task_repository import ExecutionLease
from app.repositories.document_parsing_repository import DocumentParsingRepository
from app.schemas.document_parsing import ParseFailureCode, ResumeProfileExtractionV1


class ResumeParseFinalizationService:
    """Keep Worker code free of persistence while enforcing the resume task boundary."""

    def __init__(self, *, repository: DocumentParsingRepository) -> None:
        self._repository = repository

    async def succeed(self, lease: ExecutionLease, profile: ResumeProfileExtractionV1) -> bool:
        """Write the profile and success terminal state only for the current execution lease."""
        _require_resume_parse_lease(lease)
        return await self._repository.complete_resume_for_execution(
            task_run_id=lease.task_run_id,
            resume_id=lease.resource_id,
            execution_token=lease.execution_token,
            profile=profile,
        )

    async def fail(self, lease: ExecutionLease, failure_code: ParseFailureCode) -> bool:
        """Write a classified terminal failure only for the current execution lease."""
        _require_resume_parse_lease(lease)
        return await self._repository.fail_resume_for_execution(
            task_run_id=lease.task_run_id,
            resume_id=lease.resource_id,
            execution_token=lease.execution_token,
            failure_code=failure_code,
        )


def _require_resume_parse_lease(lease: ExecutionLease) -> None:
    if lease.task_type != "resume_parse" or lease.resource_type != "resume":
        raise ValueError("execution lease is not for resume parsing")
