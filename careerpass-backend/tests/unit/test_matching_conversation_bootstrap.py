"""S-08 regression checks for the Application-to-Conversation handoff."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.infrastructure.database.models import Application, Match
from app.repositories.matching_repository import MatchingRepository


def test_existing_application_reuses_conversation_container() -> None:
    session = MagicMock()
    session.scalar = AsyncMock()
    application = Application(
        id=uuid4(),
        run_id=uuid4(),
        match_id=uuid4(),
        candidate_id=uuid4(),
        job_id=uuid4(),
        status="submitted",
    )
    match = Match(
        id=uuid4(),
        run_id=application.run_id,
        candidate_id=application.candidate_id,
        job_id=application.job_id,
        algorithm_version="test",
        input_snapshot={},
        status="matched",
        recommendation_reason="test",
        reason_code="test",
    )
    session.scalar.return_value = application
    repository = MatchingRepository(session)
    repository.ensure_conversation = AsyncMock()

    result = asyncio.run(repository.ensure_application(match=match))

    assert result is application
    repository.ensure_conversation.assert_awaited_once_with(application_id=application.id)


def test_new_application_initializes_conversation_in_same_repository_flow() -> None:
    session = MagicMock()
    session.scalar = AsyncMock()
    session.scalar.return_value = None
    async def assign_server_defaults() -> None:
        for call in session.add.call_args_list:
            value = call.args[0]
            if isinstance(value, Application) and value.id is None:
                value.id = uuid4()

    session.flush = AsyncMock(side_effect=assign_server_defaults)
    match = Match(
        id=uuid4(),
        run_id=uuid4(),
        candidate_id=uuid4(),
        job_id=uuid4(),
        algorithm_version="test",
        input_snapshot={},
        status="matched",
        recommendation_reason="test",
        reason_code="test",
    )
    repository = MatchingRepository(session)
    repository.ensure_conversation = AsyncMock()

    result = asyncio.run(repository.ensure_application(match=match))

    assert result.id is not None
    repository.ensure_conversation.assert_awaited_once_with(application_id=result.id)
