"""Document-parsing application use cases exposed to authenticated API handlers."""

from uuid import UUID

from app.repositories.document_parsing_repository import DocumentParsingRepository
from app.schemas.document_parsing import CandidateProfileResponse


class DocumentParsingService:
    """Read only validated profiles owned by the document-parsing module."""

    def __init__(self, *, repository: DocumentParsingRepository) -> None:
        self._repository = repository

    async def get_profile(
        self, candidate_id: UUID, resume_id: UUID
    ) -> CandidateProfileResponse | None:
        value = await self._repository.get_profile(candidate_id, resume_id)
        if value is None:
            return None
        return CandidateProfileResponse(
            profile_id=value.id,
            resume_id=value.resume_id,
            full_name=getattr(value, "full_name", None),
            phone=getattr(value, "phone", None),
            email=getattr(value, "email", None),
            matching_readiness=getattr(value, "matching_readiness", "matching_not_ready"),
            target_job_titles=value.target_job_titles or [],
            skills=value.skills or [],
            work_experience_summary=value.work_experience_summary or [],
            project_experience_summary=value.project_experience_summary or [],
            years_of_experience=value.years_of_experience or "unknown",
            education=value.education,
            expected_location=value.expected_location,
            expected_salary=value.expected_salary,
        )
