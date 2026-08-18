"""Add S-07 Agent startup contexts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260817_0012"
down_revision: str | None = "20260816_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_run_contexts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_goal_id", sa.UUID(), nullable=False),
        sa.Column("resume_id", sa.UUID(), nullable=False),
        sa.Column("candidate_profile_id", sa.UUID(), nullable=False),
        sa.Column("goal_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'running'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], name="fk_agent_run_candidate", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_goal_id"], ["job_goals.id"], name="fk_agent_run_job_goal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], name="fk_agent_run_resume", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], name="fk_agent_run_profile", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_run_contexts"),
        sa.UniqueConstraint("candidate_id", "job_goal_id", name="uq_agent_run_candidate_goal"),
        sa.CheckConstraint("status IN ('running', 'finished')", name="ck_agent_run_status"),
    )
    op.create_index("idx_agent_run_candidate_status", "agent_run_contexts", ["candidate_id", "status"])
    op.create_index("idx_agent_run_resume", "agent_run_contexts", ["resume_id"])


def downgrade() -> None:
    op.drop_index("idx_agent_run_resume", table_name="agent_run_contexts")
    op.drop_index("idx_agent_run_candidate_status", table_name="agent_run_contexts")
    op.drop_table("agent_run_contexts")
