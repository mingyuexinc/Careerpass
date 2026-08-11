"""Tests for the Alembic empty baseline and revision graph."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_graph_has_the_candidate_preparation_head() -> None:
    project_root = Path(__file__).parents[2]
    config = Config(str(project_root / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "20260811_0005"


def test_empty_baseline_contains_no_schema_operations() -> None:
    revision_file = (
        Path(__file__).parents[2] / "alembic" / "versions" / "20260723_0001_empty_baseline.py"
    )
    source = revision_file.read_text(encoding="utf-8")

    assert "op." not in source


def test_t02_migration_creates_only_identity_objects_and_audit_triggers() -> None:
    revision_file = (
        Path(__file__).parents[2] / "alembic" / "versions" / "20260725_0002_auth_user_candidate.py"
    )
    source = revision_file.read_text(encoding="utf-8")

    assert '"users"' in source
    assert '"candidates"' in source
    assert "auth_sessions" not in source
    assert "trg_users_set_updated_at" in source
    assert "trg_candidates_set_updated_at" in source
