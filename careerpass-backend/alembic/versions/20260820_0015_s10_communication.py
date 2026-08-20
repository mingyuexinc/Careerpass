"""Add S10 conversation, messages and AgentTurn records."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0015"
down_revision: str | None = "20260819_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name="fk_conversations_application", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        sa.UniqueConstraint("application_id", name="uq_conversations_application_id"),
    )
    op.create_index("idx_conversations_application", "conversations", ["application_id"])
    # S-08 may already have persisted Applications before this migration.  Backfill
    # only the container; welcome messages remain an S10 concern and are not created.
    op.execute(
        sa.text(
            """
            INSERT INTO conversations (application_id)
            SELECT a.id
            FROM applications AS a
            LEFT JOIN conversations AS c ON c.application_id = a.id
            WHERE c.id IS NULL
            """
        )
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("sender", sa.String(length=16), nullable=False),
        sa.Column("message_type", sa.String(length=16), server_default=sa.text("'text'"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'sent'"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("client_message_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_messages_conversation", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.UniqueConstraint("conversation_id", "sender", "client_message_id", name="uq_messages_client_id"),
        sa.CheckConstraint("sender IN ('hr', 'agent')", name="ck_messages_sender"),
        sa.CheckConstraint("message_type = 'text'", name="ck_messages_type"),
        sa.CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_messages_status"),
    )
    op.create_index("idx_messages_conversation_created", "messages", ["conversation_id", "created_at"])

    op.create_table(
        "agent_turns",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("source_message_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("scene", sa.String(length=32), server_default=sa.text("'resume_answer'"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'accepted'"), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("retryable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_agent_turns_conversation", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_message_id"], ["messages.id"], name="fk_agent_turns_source_message", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_turns"),
        sa.UniqueConstraint("source_message_id", name="uq_agent_turns_source_message"),
        sa.UniqueConstraint("idempotency_key", name="uq_agent_turns_idempotency_key"),
        sa.CheckConstraint("scene = 'resume_answer'", name="ck_agent_turns_scene"),
        sa.CheckConstraint("status IN ('accepted', 'processing', 'completed', 'failed')", name="ck_agent_turns_status"),
    )
    op.create_index("idx_agent_turns_conversation_created", "agent_turns", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_agent_turns_conversation_created", table_name="agent_turns")
    op.drop_table("agent_turns")
    op.drop_index("idx_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("idx_conversations_application", table_name="conversations")
    op.drop_table("conversations")
