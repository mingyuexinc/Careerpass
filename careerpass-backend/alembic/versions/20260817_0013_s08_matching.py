"""Add S-08 matching, applications and progress events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260817_0013"
down_revision: str | None = "20260817_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_run_contexts", sa.Column("finish_reason", sa.String(length=32), nullable=True))
    op.create_check_constraint(
        "ck_agent_run_finish_reason",
        "agent_run_contexts",
        "finish_reason IS NULL OR finish_reason IN ('offer_target_reached', 'no_match')",
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("role_score", sa.Float(), nullable=True),
        sa.Column("level_score", sa.Float(), nullable=True),
        sa.Column("skill_score", sa.Float(), nullable=True),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("recommendation_reason", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_run_contexts.id"], name="fk_matches_run", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], name="fk_matches_candidate", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_matches_job", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_matches"),
        sa.UniqueConstraint("run_id", "job_id", name="uq_matches_run_job"),
        sa.CheckConstraint(
            "status IN ('filtered_out', 'not_matched', 'matched', 'application_created')",
            name="ck_matches_status",
        ),
    )
    op.create_index("idx_matches_candidate", "matches", ["candidate_id", "created_at"])
    op.create_index("idx_matches_run", "matches", ["run_id", "job_id"])

    op.create_table(
        "applications",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("match_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'submitted'"), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_run_contexts.id"], name="fk_applications_run", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_applications_match", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], name="fk_applications_candidate", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_applications_job", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_applications"),
        sa.UniqueConstraint("run_id", "job_id", name="uq_applications_run_job"),
        sa.UniqueConstraint("match_id", name="uq_applications_match"),
    )
    op.create_index("idx_applications_candidate", "applications", ["candidate_id", "created_at"])

    op.create_table(
        "progress_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name="fk_progress_events_application", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], name="fk_progress_events_candidate", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_progress_events_job", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_progress_events"),
    )
    op.create_index("idx_progress_events_application", "progress_events", ["application_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_progress_events_application", table_name="progress_events")
    op.drop_table("progress_events")
    op.drop_index("idx_applications_candidate", table_name="applications")
    op.drop_table("applications")
    op.drop_index("idx_matches_run", table_name="matches")
    op.drop_index("idx_matches_candidate", table_name="matches")
    op.drop_table("matches")
    op.drop_constraint("ck_agent_run_finish_reason", "agent_run_contexts", type_="check")
    op.drop_column("agent_run_contexts", "finish_reason")
