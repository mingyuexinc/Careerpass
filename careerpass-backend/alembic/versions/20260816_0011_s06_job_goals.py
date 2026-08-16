"""Add candidate-owned current job goals for S-06."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0011"
down_revision: str | None = "20260815_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_goals",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("offer_target", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("filters", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidates.id"], name="fk_job_goal_candidate", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_goals"),
        sa.UniqueConstraint("candidate_id", name="uq_job_goals_candidate_id"),
        sa.CheckConstraint("offer_target BETWEEN 1 AND 10", name="ck_job_goals_offer_target"),
        sa.CheckConstraint(
            "status IN ('active', 'achieved', 'abandoned')", name="ck_job_goals_status"
        ),
    )
    op.create_index("idx_job_goals_candidate_status", "job_goals", ["candidate_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_job_goals_candidate_status", table_name="job_goals")
    op.drop_table("job_goals")
