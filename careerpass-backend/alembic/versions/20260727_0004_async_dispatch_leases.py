"""Add durable dispatcher lease state for at-least-once task publication.

Revision ID: 20260727_0004
Revises: 20260727_0003
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0004"
down_revision: str | None = "20260727_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "async_task_runs",
        sa.Column("dispatch_token", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "async_task_runs",
        sa.Column("dispatch_lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "async_task_runs",
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_async_task_run_dispatch_lease",
        "async_task_runs",
        ["status", "dispatched_at", "dispatch_lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_async_task_run_dispatch_lease", table_name="async_task_runs")
    op.drop_column("async_task_runs", "dispatched_at")
    op.drop_column("async_task_runs", "dispatch_lease_expires_at")
    op.drop_column("async_task_runs", "dispatch_token")
