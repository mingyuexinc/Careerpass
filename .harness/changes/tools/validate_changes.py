"""Validate this change-management directory without external dependencies."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"proposed", "ready", "in-progress", "released", "archived"}
TYPES = {
    "contract",
    "feature",
    "business-module",
    "bugfix",
    "tech-debt",
    "infrastructure",
    "operations",
}
PACKAGE_NAME = re.compile(r"^(CHG-\d{4}-\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_METADATA = {
    "id",
    "title",
    "type",
    "status",
    "created_at",
    "affected_modules",
    "risk_level",
    "dependencies",
    "supersedes",
}


def parse_top_level_keys(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line or raw_line.startswith(("#", " ", "\t")) or ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        values[key.strip()] = value.strip().split(" #", 1)[0].strip()
    return values


def require(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing required file: {path.relative_to(ROOT)}")


def validate_package(status: str, package: Path, seen_ids: set[str], errors: list[str]) -> None:
    match = PACKAGE_NAME.fullmatch(package.name)
    if not match:
        errors.append(f"invalid package name: {package.relative_to(ROOT)}")
        return

    package_id = match.group(1)
    if package_id in seen_ids:
        errors.append(f"duplicate package id: {package_id}")
    seen_ids.add(package_id)

    metadata_path = package / "change.yaml"
    require(metadata_path, errors)
    require(package / "summary.md", errors)
    require(package / "01-analysis" / "impact-analysis.md", errors)
    if not metadata_path.is_file():
        return

    metadata = parse_top_level_keys(metadata_path)
    missing = REQUIRED_METADATA - metadata.keys()
    if missing:
        errors.append(f"{package.relative_to(ROOT)}: missing metadata: {', '.join(sorted(missing))}")
    if metadata.get("id") != package_id:
        errors.append(f"{package.relative_to(ROOT)}: id must equal {package_id}")
    if metadata.get("status") != status:
        errors.append(f"{package.relative_to(ROOT)}: status must equal parent directory '{status}'")
    if metadata.get("type") not in TYPES:
        errors.append(f"{package.relative_to(ROOT)}: invalid type '{metadata.get('type', '')}'")
    if metadata.get("risk_level") not in {"low", "medium", "high"}:
        errors.append(f"{package.relative_to(ROOT)}: invalid risk_level")

    change_type = metadata.get("type")
    if change_type in {"feature", "business-module"}:
        for relative in (
            "02-design/design.md",
            "03-plan/task-breakdown.md",
            "05-implementation/implementation-notes.md",
            "06-verification/test-plan.md",
        ):
            require(package / relative, errors)

    data_dir = package / "04-data"
    if data_dir.exists():
        for filename in ("db-migrations.sql", "rollback.sql", "alembic-revisions.md"):
            require(data_dir / filename, errors)


def main() -> int:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for status_dir in sorted(ROOT.iterdir()):
        if not status_dir.is_dir() or status_dir.name.startswith("_"):
            continue
        if status_dir.name not in STATUSES:
            continue
        for package in sorted(path for path in status_dir.iterdir() if path.is_dir()):
            validate_package(status_dir.name, package, seen_ids, errors)
    if errors:
        print("Change package validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Change package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
