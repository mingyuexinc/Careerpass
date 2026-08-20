"""Add S10-02 downloadable message attachments.

Revision ID: 20260820_0016
Revises: 20260820_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0016"
down_revision: str | None = "20260820_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_agent_turns_scene", "agent_turns", type_="check")
    op.create_check_constraint(
        "ck_agent_turns_scene",
        "agent_turns",
        "scene IN ('resume_answer', 'document_delivery')",
    )

    op.create_table(
        "message_attachments",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("candidate_document_id", sa.UUID(), nullable=True),
        sa.Column("stored_file_object_id", sa.UUID(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'preparing'"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], name="fk_message_attachments_message", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_document_id"], ["candidate_documents.id"], name="fk_message_attachments_candidate_document", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stored_file_object_id"], ["stored_file_objects.id"], name="fk_message_attachments_stored_file_object", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_message_attachments"),
        sa.UniqueConstraint("message_id", name="uq_message_attachments_message_id"),
        sa.CheckConstraint("status IN ('preparing', 'downloadable', 'failed', 'expired')", name="ck_message_attachments_status"),
    )
    op.create_index("idx_message_attachments_expires", "message_attachments", ["expires_at"])
    op.create_index("idx_message_attachments_status", "message_attachments", ["status"])


def downgrade() -> None:
    op.drop_index("idx_message_attachments_status", table_name="message_attachments")
    op.drop_index("idx_message_attachments_expires", table_name="message_attachments")
    op.drop_table("message_attachments")
    op.drop_constraint("ck_agent_turns_scene", "agent_turns", type_="check")
    op.create_check_constraint(
        "ck_agent_turns_scene",
        "agent_turns",
        "scene = 'resume_answer'",
    )
