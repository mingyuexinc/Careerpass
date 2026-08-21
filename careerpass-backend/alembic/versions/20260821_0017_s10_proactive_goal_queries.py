"""Extend AgentTurn for idempotent S10-03 proactive goal queries."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260821_0017"
down_revision: str | None = "20260820_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("agent_turns", "source_message_id", nullable=True)
    op.add_column(
        "agent_turns",
        sa.Column("result_message_id", sa.UUID(), nullable=True),
    )
    op.create_unique_constraint("uq_agent_turns_result_message_id", "agent_turns", ["result_message_id"])
    op.create_foreign_key(
        "fk_agent_turns_result_message",
        "agent_turns",
        "messages",
        ["result_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("ck_agent_turns_scene", "agent_turns", type_="check")
    op.create_check_constraint(
        "ck_agent_turns_scene", "agent_turns",
        "scene IN ('resume_answer', 'document_delivery', 'goal_query', 'goal_judgement')",
    )
    op.drop_constraint("ck_agent_turns_status", "agent_turns", type_="check")
    op.create_check_constraint(
        "ck_agent_turns_status", "agent_turns",
        "status IN ('accepted', 'processing', 'waiting', 'completed', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_agent_turns_status", "agent_turns", type_="check")
    op.create_check_constraint(
        "ck_agent_turns_status", "agent_turns",
        "status IN ('accepted', 'processing', 'completed', 'failed')",
    )
    op.drop_constraint("ck_agent_turns_scene", "agent_turns", type_="check")
    op.create_check_constraint(
        "ck_agent_turns_scene", "agent_turns",
        "scene IN ('resume_answer', 'document_delivery')",
    )
    op.drop_constraint("fk_agent_turns_result_message", "agent_turns", type_="foreignkey")
    op.drop_constraint("uq_agent_turns_result_message_id", "agent_turns", type_="unique")
    op.drop_column("agent_turns", "result_message_id")
    op.alter_column("agent_turns", "source_message_id", nullable=False)
