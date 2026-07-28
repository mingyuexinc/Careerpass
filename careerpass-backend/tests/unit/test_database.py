"""Tests for the L3 database infrastructure boundary."""

import asyncio

from app.infrastructure.database import Base, Candidate, User, create_database

TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/careerpass_test"


def test_database_creates_async_postgresql_engine_and_session_factory() -> None:
    database = create_database(TEST_DATABASE_URL, pool_size=2)

    assert database.engine.dialect.name == "postgresql"
    assert database.engine.url.drivername == "postgresql+asyncpg"
    assert database.session_factory.kw["expire_on_commit"] is False


def test_database_close_is_idempotent() -> None:
    database = create_database(TEST_DATABASE_URL)

    asyncio.run(database.close())
    asyncio.run(database.close())

    assert database._closed is True


def test_base_metadata_contains_candidate_preparation_models() -> None:
    assert set(Base.metadata.tables) == {
        "async_task_runs",
        "candidate_documents",
        "candidate_profiles",
        "candidates",
        "resumes",
        "stored_file_objects",
        "users",
    }
    assert User.__table__.c.username.type.length == 64
    assert Candidate.__table__.c.name.type.length == 64
    assert Candidate.__table__.c.user_id.unique is True
