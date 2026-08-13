"""Add HR-owned Jobs and JD parse handoff support."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260813_0006"
down_revision: str | None = "20260811_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE async_task_type_enum ADD VALUE IF NOT EXISTS 'job_jd_parse'")
    op.execute("ALTER TYPE async_task_resource_type_enum ADD VALUE IF NOT EXISTS 'job'")

    op.create_table(
        "jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("hr_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stored_file_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["hr_profile_id"],
            ["hr_profiles.id"],
            name="fk_job_hr_profile",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stored_file_object_id"],
            ["stored_file_objects.id"],
            name="fk_job_stored_file_object",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
    )
    op.create_index("idx_job_hr_profile_created_at", "jobs", ["hr_profile_id", "created_at"])
    op.create_index("idx_job_stored_file_object", "jobs", ["stored_file_object_id"])
    op.create_index(
        "uq_job_active_hr_file",
        "jobs",
        ["hr_profile_id", "stored_file_object_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_job_active_hr_file", table_name="jobs")
    op.drop_index("idx_job_stored_file_object", table_name="jobs")
    op.drop_index("idx_job_hr_profile_created_at", table_name="jobs")
    op.drop_table("jobs")
