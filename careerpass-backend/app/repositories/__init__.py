"""Repository boundary for all database access outside infrastructure."""

from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.document_parsing_repository import DocumentParsingRepository
from app.repositories.identity_repository import IdentityRepository
from app.repositories.job_upload_repository import JobUploadRepository
from app.repositories.user_repository import UsernameConflictError, UserRepository

__all__ = [
    "AsyncTaskRepository",
    "CandidateRepository",
    "DocumentParsingRepository",
    "IdentityRepository",
    "JobUploadRepository",
    "UserRepository",
    "UsernameConflictError",
]
