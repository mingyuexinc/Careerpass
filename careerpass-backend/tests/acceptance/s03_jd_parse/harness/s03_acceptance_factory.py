"""Fixture and resource factory for the S-03 internal-capability scenario."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.core.security import create_access_token
from app.infrastructure.database.session import Database, create_database
from app.infrastructure.storage.local import LocalObjectStorage
from tests.acceptance.s03_jd_parse.harness.s03_acceptance_repository import (
    ControlledHrIdentity,
    CreatedJob,
    S03AcceptanceRepository,
)


@dataclass(frozen=True)
class S03Fixture:
    name: str
    expected: dict[str, object]


@dataclass
class PreparedS03Fixture:
    fixture: S03Fixture
    content: bytes
    created: CreatedJob
    hr: ControlledHrIdentity
    token: str
    container_path: str


class S03AcceptanceFactory:
    """Create legal S-02 output state without invoking S-02's HTTP workflow."""

    def __init__(self, project_root: Path) -> None:
        backend_root = project_root / "careerpass-backend"
        self.acceptance_root = backend_root / "tests" / "acceptance" / "s03_jd_parse"
        self.fixture_root = backend_root / "tests" / "fixtures" / "job_descriptions"
        self.expected_path = self.acceptance_root / "harness" / "s03_acceptance_expected.json"
        self.object_root = Path(
            os.environ.get("TEST_OBJECT_STORAGE_ROOT", str(backend_root / ".careerpass-objects"))
        )
        self.container_fixture_root = os.environ.get(
            "S03_ACCEPTANCE_CONTAINER_JD_ROOT", "/opt/careerpass/s03-jd"
        )
        self.database: Database = create_database(
            os.environ.get("TEST_DATABASE_URL", os.environ["DATABASE_URL"])
        )
        self.storage = LocalObjectStorage(str(self.object_root))
        self._prepared: list[PreparedS03Fixture] = []

    def fixtures(self) -> list[S03Fixture]:
        manifest = json.loads(self.expected_path.read_text(encoding="utf-8"))
        fixtures: list[S03Fixture] = []
        for name in manifest["fixtures"]:
            if not name.startswith(("001-", "002-")) or not name.endswith(".md"):
                raise AssertionError("S-03 acceptance may use only fixtures 001 and 002")
            path = self.fixture_root / name
            if not path.is_file():
                raise AssertionError(f"required fixed fixture is missing: {name}")
            fixtures.append(S03Fixture(name=name, expected=manifest[name]))
        if [item.name for item in fixtures] != manifest["fixtures"]:
            raise AssertionError("S-03 acceptance fixture order or membership changed")
        return fixtures

    async def prepare(self, fixture: S03Fixture) -> PreparedS03Fixture:
        content = (self.fixture_root / fixture.name).read_bytes()
        upload = self.storage.put(content)
        created: CreatedJob | None = None
        try:
            async with self.database.session_factory() as session:
                async with session.begin():
                    repo = S03AcceptanceRepository(session)
                    hr = await repo.get_controlled_hr("hr_01")
                    created = await repo.create_job(
                        hr_profile_id=hr.hr_profile_id,
                        upload=upload,
                        detected_mime_type="text/markdown",
                    )
            if not created.created_file_object or created.storage_key != upload.storage_key:
                async with self.database.session_factory() as session:
                    await S03AcceptanceRepository(session).cleanup(
                        job_id=created.job_id,
                        file_object_id=created.file_object_id,
                        delete_file_object=False,
                    )
                raise AssertionError(
                    "acceptance setup did not create an isolated ready file object"
                )
        except Exception:
            self.storage.delete(upload.storage_key)
            raise
        token = create_access_token(
            user_id=hr.user_id,
            settings=get_settings(),
            active_role="hr",
        )
        prepared = PreparedS03Fixture(
            fixture=fixture,
            content=content,
            created=created,
            hr=hr,
            token=token,
            container_path=f"{self.container_fixture_root}/{fixture.name}",
        )
        self._prepared.append(prepared)
        return prepared

    async def inspect(self, prepared: PreparedS03Fixture, task_id: UUID) -> dict[str, object]:
        async with self.database.session_factory() as session:
            return await S03AcceptanceRepository(session).inspect_result(
                hr_profile_id=prepared.hr.hr_profile_id,
                job_id=prepared.created.job_id,
                task_id=task_id,
            )

    async def cleanup(self, prepared: PreparedS03Fixture) -> None:
        cleanup_error: Exception | None = None
        try:
            async with self.database.session_factory() as session:
                await S03AcceptanceRepository(session).cleanup(
                    job_id=prepared.created.job_id,
                    file_object_id=prepared.created.file_object_id,
                    delete_file_object=prepared.created.created_file_object,
                )
        except Exception as exc:  # pragma: no cover - surfaced by the scenario report
            cleanup_error = exc
        finally:
            self.storage.delete(prepared.created.storage_key)
            if prepared in self._prepared:
                self._prepared.remove(prepared)
        if cleanup_error is not None:
            raise cleanup_error

    async def close(self) -> None:
        for prepared in list(self._prepared):
            await self.cleanup(prepared)
        await self.database.close()
