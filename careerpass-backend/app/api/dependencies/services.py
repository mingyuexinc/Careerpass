"""API dependency factories that assemble application services with repositories."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.infrastructure.storage.controlled import ControlledJobDescriptionStorage
from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.candidate_preparation_repository import CandidatePreparationRepository
from app.repositories.debug_reset_repository import DebugResetRepository
from app.repositories.document_parsing_repository import DocumentParsingRepository
from app.repositories.identity_repository import IdentityRepository
from app.repositories.job_description_repository import JobDescriptionRepository
from app.repositories.job_goal_repository import JobGoalRepository
from app.repositories.job_upload_repository import JobUploadRepository
from app.repositories.object_storage_repository import ObjectStorageRepository
from app.repositories.user_repository import UserRepository
from app.services.candidate_preparation_service import CandidatePreparationService
from app.services.debug_reset_service import DebugResetService
from app.services.document_parsing_service import DocumentParsingService
from app.services.job_description_service import JobDescriptionService
from app.services.job_goal_service import JobGoalService
from app.services.job_upload_service import JobUploadService
from app.services.login_service import LoginService
from app.services.registration_service import RegistrationService


async def get_registration_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[RegistrationService]:
    """Build a registration service whose Repository session closes with the request."""
    async with request.app.state.database.session_factory() as session:
        yield RegistrationService(user_repository=UserRepository(session), settings=settings)


async def get_login_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[LoginService]:
    """Build a login service whose Repository session closes with the request."""
    async with request.app.state.database.session_factory() as session:
        yield LoginService(
            user_repository=UserRepository(session),
            identity_repository=IdentityRepository(session),
            settings=settings,
        )


async def get_candidate_preparation_service(
    request: Request,
) -> AsyncIterator[CandidatePreparationService]:
    """Build the candidate preparation service with request-scoped persistence."""
    async with request.app.state.database.session_factory() as session:
        yield CandidatePreparationService(
            repository=CandidatePreparationRepository(session),
            task_repository=AsyncTaskRepository(session),
            storage=request.app.state.object_storage,
        )


async def get_document_parsing_service(
    request: Request,
) -> AsyncIterator[DocumentParsingService]:
    """Build the document-parsing service with request-scoped persistence."""
    async with request.app.state.database.session_factory() as session:
        yield DocumentParsingService(repository=DocumentParsingRepository(session))


async def get_job_upload_service(
    request: Request,
) -> AsyncIterator[JobUploadService]:
    """Build the request-scoped HR Job upload service."""
    async with request.app.state.database.session_factory() as session:
        yield JobUploadService(
            repository=JobUploadRepository(session),
            task_repository=AsyncTaskRepository(session),
            storage=request.app.state.object_storage,
        )


async def get_job_description_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[JobDescriptionService]:
    """Build the request-scoped internal S-03 verification service."""
    async with request.app.state.database.session_factory() as session:
        yield JobDescriptionService(
            repository=JobDescriptionRepository(session),
            storage=ControlledJobDescriptionStorage(settings.s03_jd_root),
        )


async def get_job_goal_service(request: Request) -> AsyncIterator[JobGoalService]:
    """Build the request-scoped S-06 job-goal service."""
    async with request.app.state.database.session_factory() as session:
        yield JobGoalService(repository=JobGoalRepository(session))


async def get_debug_reset_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[DebugResetService]:
    """Build the development-only current-account reset service."""
    async with request.app.state.database.session_factory() as session:
        yield DebugResetService(
            repository=DebugResetRepository(session),
            object_repository=ObjectStorageRepository(session),
            storage=request.app.state.object_storage,
            enabled=settings.debug_reset_enabled,
        )
