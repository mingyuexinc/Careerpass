"""Persist the original filename on each HR-owned Job."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0014"
down_revision: str | None = "20260817_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("file_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "file_name")
