"""Unit tests for identity repositories without an external database dependency."""

import asyncio
from collections.abc import Iterable
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Candidate, User
from app.repositories import CandidateRepository, UsernameConflictError, UserRepository


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class _Transaction:
    def __init__(self, session: "_SessionDouble") -> None:
        self._session = session

    async def __aenter__(self) -> None:
        self._session.transaction_started = True

    async def __aexit__(self, *_: object) -> None:
        self._session.transaction_finished = True


class _SessionDouble:
    def __init__(
        self,
        results: Iterable[object | None] = (),
        flush_error: Exception | None = None,
    ) -> None:
        self._results = iter(results)
        self._flush_error = flush_error
        self.added: tuple[object, ...] = ()
        self.transaction_started = False
        self.transaction_finished = False
        self.flush_called = False

    def begin(self) -> _Transaction:
        return _Transaction(self)

    def add_all(self, instances: Iterable[object]) -> None:
        self.added = tuple(instances)

    async def flush(self) -> None:
        self.flush_called = True
        if self._flush_error is not None:
            raise self._flush_error

    async def execute(self, _: object) -> _ScalarResult:
        return _ScalarResult(next(self._results, None))


def test_user_repository_resolves_accounts_by_id_and_username() -> None:
    user = User(id=uuid4(), username="alice", password_hash="scrypt$hash")
    session = _SessionDouble((user, user))
    repository = UserRepository(cast(AsyncSession, session))

    assert asyncio.run(repository.get_by_id(user.id)) is user
    assert asyncio.run(repository.get_by_username(user.username)) is user


def test_user_repository_creates_user_and_candidate_in_one_transaction() -> None:
    session = _SessionDouble()
    repository = UserRepository(cast(AsyncSession, session))

    identity = asyncio.run(
        repository.create_with_candidate(
            username="alice",
            password_hash="scrypt$hash",
            name="Alice",
        )
    )
    assert identity is not None
    user, candidate = identity

    assert isinstance(user, User)
    assert isinstance(candidate, Candidate)
    assert candidate.user is user
    assert session.added == (user, candidate)
    assert session.transaction_started and session.transaction_finished
    assert session.flush_called


def test_user_repository_returns_none_when_username_is_already_reserved() -> None:
    session = _SessionDouble((uuid4(),))
    repository = UserRepository(cast(AsyncSession, session))

    identity = asyncio.run(
        repository.create_with_candidate(
            username="alice",
            password_hash="scrypt$hash",
            name="Alice",
        )
    )

    assert identity is None
    assert session.added == ()
    assert not session.flush_called


def test_user_repository_maps_username_unique_constraint_to_domain_error() -> None:
    class _DuplicateUsernameError(Exception):
        constraint_name = "uq_user_username"

    session = _SessionDouble(flush_error=IntegrityError("INSERT", {}, _DuplicateUsernameError()))
    repository = UserRepository(cast(AsyncSession, session))

    with pytest.raises(UsernameConflictError):
        asyncio.run(
            repository.create_with_candidate(
                username="alice",
                password_hash="scrypt$hash",
                name="Alice",
            )
        )


def test_candidate_repository_resolves_candidates_by_id_and_user_id() -> None:
    candidate = Candidate(id=uuid4(), user_id=uuid4(), name="Alice")
    session = _SessionDouble((candidate, candidate))
    repository = CandidateRepository(cast(AsyncSession, session))

    assert asyncio.run(repository.get_by_id(candidate.id)) is candidate
    assert asyncio.run(repository.get_by_user_id(candidate.user_id)) is candidate
