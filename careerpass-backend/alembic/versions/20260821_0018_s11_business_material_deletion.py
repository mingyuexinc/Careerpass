"""Add S-11 logical deletion, current resume selection and audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260821_0018"
down_revision: str | None = "20260821_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.add_column("resumes", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "candidate_documents",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("candidates", sa.Column("current_resume_id", uuid_type, nullable=True))
    op.create_foreign_key(
        "fk_candidate_current_resume",
        "candidates",
        "resumes",
        ["current_resume_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        "UPDATE candidates AS c SET current_resume_id = latest.id "
        "FROM (SELECT DISTINCT ON (candidate_id) id, candidate_id "
        "FROM resumes WHERE deleted_at IS NULL ORDER BY candidate_id, created_at DESC, id DESC) AS latest "
        "WHERE c.id = latest.candidate_id"
    )
    op.drop_index("uq_resume_candidate_upload_idempotency_key", table_name="resumes")
    op.drop_index("uq_resume_candidate_stored_file", table_name="resumes")
    op.create_index(
        "uq_resume_candidate_upload_idempotency_key",
        "resumes",
        ["candidate_id", "upload_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("upload_idempotency_key IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "uq_resume_candidate_stored_file",
        "resumes",
        ["candidate_id", "stored_file_object_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "uq_candidate_document_candidate_upload_idempotency_key",
        table_name="candidate_documents",
    )
    op.create_index(
        "uq_candidate_document_candidate_upload_idempotency_key",
        "candidate_documents",
        ["candidate_id", "upload_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("upload_idempotency_key IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_table(
        "resource_audit_events",
        sa.Column("id", uuid_type, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", uuid_type, nullable=False),
        sa.Column("actor_user_id", uuid_type, nullable=False),
        sa.Column("actor_role", sa.String(length=16), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_resource_audit_actor_user", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_resource_audit_events"),
        sa.UniqueConstraint(
            "resource_type",
            "resource_id",
            "event_type",
            name="uq_resource_audit_event_resource_type_id_event",
        ),
    )
    op.create_index(
        "idx_resource_audit_event_resource",
        "resource_audit_events",
        ["resource_type", "resource_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_resource_audit_event_resource", table_name="resource_audit_events")
    op.drop_table("resource_audit_events")
    op.drop_index(
        "uq_candidate_document_candidate_upload_idempotency_key",
        table_name="candidate_documents",
    )
    op.create_index(
        "uq_candidate_document_candidate_upload_idempotency_key",
        "candidate_documents",
        ["candidate_id", "upload_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("upload_idempotency_key IS NOT NULL"),
    )
    op.drop_index("uq_resume_candidate_upload_idempotency_key", table_name="resumes")
    op.create_index(
        "uq_resume_candidate_upload_idempotency_key",
        "resumes",
        ["candidate_id", "upload_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("upload_idempotency_key IS NOT NULL"),
    )
    op.drop_index("uq_resume_candidate_stored_file", table_name="resumes")
    op.create_index(
        "uq_resume_candidate_stored_file",
        "resumes",
        ["candidate_id", "stored_file_object_id"],
        unique=True,
    )
    op.drop_constraint("fk_candidate_current_resume", "candidates", type_="foreignkey")
    op.drop_column("candidates", "current_resume_id")
    op.drop_column("candidate_documents", "deleted_at")
    op.drop_column("resumes", "deleted_at")
