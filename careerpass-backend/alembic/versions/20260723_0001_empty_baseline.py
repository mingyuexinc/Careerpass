"""Phase 0 empty Alembic baseline; no business DDL is permitted here.

Revision ID: 20260723_0001
Revises:
Create Date: 2026-07-23
"""

from collections.abc import Sequence

revision: str = "20260723_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establish the version baseline without creating database objects."""
    pass


def downgrade() -> None:
    """Reverse the empty baseline without deleting database objects."""
    pass
