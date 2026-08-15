"""Add S-03 parsed JD snapshots and task failure metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260815_0007"
down_revision: str | None = "20260813_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "async_task_runs",
        sa.Column("task_generation", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column("async_task_runs", sa.Column("failure_semantics", sa.String(64), nullable=True))
    op.add_column("async_task_runs", sa.Column("failure_reason", sa.String(128), nullable=True))
    op.add_column(
        "async_task_runs",
        sa.Column("missing_core_fields", postgresql.JSONB(), nullable=True),
    )
    op.create_check_constraint(
        "ck_async_task_run_task_generation", "async_task_runs", "task_generation > 0"
    )
    op.create_table(
        "parsed_job_description_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("fields", postgresql.JSONB(), nullable=False),
        sa.Column("raw_sections", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name="fk_parsed_jd_snapshot_job", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_parsed_job_description_snapshots"),
        sa.UniqueConstraint("job_id", name="uq_parsed_jd_snapshot_job"),
    )
    op.create_index(
        "idx_parsed_jd_snapshot_job_created_at",
        "parsed_job_description_snapshots",
        ["job_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_parsed_jd_snapshot_job_created_at", table_name="parsed_job_description_snapshots"
    )
    op.drop_table("parsed_job_description_snapshots")
    op.drop_constraint("ck_async_task_run_task_generation", "async_task_runs", type_="check")
    op.drop_column("async_task_runs", "missing_core_fields")
    op.drop_column("async_task_runs", "failure_reason")
    op.drop_column("async_task_runs", "failure_semantics")
    op.drop_column("async_task_runs", "task_generation")
