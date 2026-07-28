"""API dependency factories that assemble application services with repositories."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.repositories.candidate_preparation_repository import CandidatePreparationRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.document_parsing_repository import DocumentParsingRepository
from app.repositories.user_repository import UserRepository
from app.services.candidate_preparation_service import CandidatePreparationService
from app.services.document_parsing_service import DocumentParsingService
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
            candidate_repository=CandidateRepository(session),
            settings=settings,
        )


async def get_candidate_preparation_service(
    request: Request,
) -> AsyncIterator[CandidatePreparationService]:
    """Build the candidate preparation service with request-scoped persistence."""
    async with request.app.state.database.session_factory() as session:
        document_parsing_repository = DocumentParsingRepository(session)
        yield CandidatePreparationService(
            repository=CandidatePreparationRepository(
                session,
                submit_resume_parse_request=document_parsing_repository.submit_resume_parse_request,
            ),
            storage=request.app.state.object_storage,
        )


async def get_document_parsing_service(
    request: Request,
) -> AsyncIterator[DocumentParsingService]:
    """Build the document-parsing service with request-scoped persistence."""
    async with request.app.state.database.session_factory() as session:
        yield DocumentParsingService(repository=DocumentParsingRepository(session))
