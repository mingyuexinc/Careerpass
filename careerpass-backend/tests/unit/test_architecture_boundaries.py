"""Regression checks for the repository-only database access rule."""

from pathlib import Path


def test_non_infrastructure_layers_do_not_import_sqlalchemy_or_sessions() -> None:
    app_root = Path(__file__).parents[2] / "app"
    protected_layers = ("api", "services", "agent", "workflows")

    for layer in protected_layers:
        layer_path = app_root / layer
        if not layer_path.exists():
            continue
        for source_file in layer_path.rglob("*.py"):
            source = source_file.read_text(encoding="utf-8")
            assert "sqlalchemy" not in source, source_file
            assert "AsyncSession" not in source, source_file
