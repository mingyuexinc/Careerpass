"""Create candidate preparation resources and durable parse task state.

Revision ID: 20260727_0003
Revises: 20260725_0002
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0003"
down_revision: str | None = "20260725_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.execute(
        "CREATE TYPE stored_file_object_status_enum AS ENUM ('writing', 'ready', 'deleting')"
    )
    op.execute("CREATE TYPE parse_status_enum AS ENUM ('processing', 'succeeded', 'failed')")
    op.execute(
        "CREATE TYPE parse_failure_code_enum AS ENUM "
        "('unsupported_file', 'file_unreadable', 'storage_unavailable', "
        "'parser_timeout', 'schema_validation_failed', 'internal_error')"
    )
    op.execute("CREATE TYPE document_type_enum AS ENUM ('certificate', 'strategy', 'other')")
    op.execute("CREATE TYPE async_task_type_enum AS ENUM ('resume_parse')")
    op.execute("CREATE TYPE async_task_resource_type_enum AS ENUM ('resume')")
    op.execute("CREATE TYPE async_task_run_status_enum AS ENUM ('queued', 'running', 'succeeded', 'failed')")
    stored_file_status = postgresql.ENUM(name="stored_file_object_status_enum", create_type=False)
    parse_status = postgresql.ENUM(name="parse_status_enum", create_type=False)
    failure_code = postgresql.ENUM(name="parse_failure_code_enum", create_type=False)
    document_type = postgresql.ENUM(name="document_type_enum", create_type=False)
    task_type = postgresql.ENUM(name="async_task_type_enum", create_type=False)
    resource_type = postgresql.ENUM(name="async_task_resource_type_enum", create_type=False)
    task_status = postgresql.ENUM(name="async_task_run_status_enum", create_type=False)
    op.create_table(
        "stored_file_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("detected_mime_type", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", stored_file_status, server_default=sa.text("'writing'"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("file_size_bytes > 0 AND file_size_bytes <= 10000000", name="ck_stored_file_size"),
        sa.PrimaryKeyConstraint("id", name="pk_stored_file_objects"),
        sa.UniqueConstraint("storage_key", name="uq_stored_file_storage_key"),
        sa.UniqueConstraint("content_sha256", name="uq_stored_file_content_sha256"),
    )
    op.execute(
        "CREATE TRIGGER trg_stored_file_objects_set_updated_at "
        "BEFORE UPDATE ON stored_file_objects FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_idempotency_key", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("stored_file_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False),
        sa.Column("parse_status", parse_status, server_default=sa.text("'processing'"), nullable=False),
        sa.Column("failure_code", failure_code, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], name="fk_resume_candidate", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stored_file_object_id"], ["stored_file_objects.id"], name="fk_resume_stored_file_object", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_resumes"),
    )
    op.create_index("idx_resume_candidate", "resumes", ["candidate_id"])
    op.create_index("idx_resume_stored_file_object", "resumes", ["stored_file_object_id"])
    op.create_index("uq_resume_candidate_upload_idempotency_key", "resumes", ["candidate_id", "upload_idempotency_key"], unique=True, postgresql_where=sa.text("upload_idempotency_key IS NOT NULL"))
    op.create_table(
        "candidate_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_job_titles", postgresql.ARRAY(sa.String(128)), nullable=False),
        sa.Column("skills", postgresql.JSONB(), nullable=True),
        sa.Column("work_experience_summary", postgresql.JSONB(), nullable=True),
        sa.Column("project_experience_summary", postgresql.JSONB(), nullable=True),
        sa.Column("years_of_experience", sa.Integer(), nullable=True),
        sa.Column("education", sa.String(64), nullable=True),
        sa.Column("expected_location", sa.String(128), nullable=True),
        sa.Column("expected_salary", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("cardinality(target_job_titles) >= 1", name="ck_candidate_profile_target_titles"),
        sa.CheckConstraint("years_of_experience IS NULL OR years_of_experience >= 0", name="ck_candidate_profile_years"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], name="fk_candidate_profile_resume", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_profiles"),
        sa.UniqueConstraint("resume_id", name="uq_candidate_profile_resume"),
    )
    op.create_table(
        "candidate_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_idempotency_key", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False),
        sa.Column("stored_file_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], name="fk_candidate_document_candidate", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stored_file_object_id"], ["stored_file_objects.id"], name="fk_candidate_document_stored_file_object", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_documents"),
    )
    op.create_index("idx_candidate_document_candidate", "candidate_documents", ["candidate_id"])
    op.create_index("uq_candidate_document_candidate_upload_idempotency_key", "candidate_documents", ["candidate_id", "upload_idempotency_key"], unique=True, postgresql_where=sa.text("upload_idempotency_key IS NOT NULL"))
    op.create_table(
        "async_task_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("task_type", task_type, nullable=False),
        sa.Column("resource_type", resource_type, nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("status", task_status, server_default=sa.text("'queued'"), nullable=False),
        sa.Column("task_version", sa.String(128), server_default=sa.text("'v1'"), nullable=False),
        sa.Column("failure_code", failure_code, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("execution_lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_async_task_runs"),
        sa.UniqueConstraint("celery_task_id", name="uq_async_task_run_celery_task"),
        sa.UniqueConstraint("idempotency_key", name="uq_async_task_run_idempotency"),
        sa.CheckConstraint(
            "(status IN ('queued', 'running') AND finished_at IS NULL) OR "
            "(status IN ('succeeded', 'failed') AND finished_at IS NOT NULL)",
            name="ck_async_task_run_finished_at",
        ),
        sa.CheckConstraint(
            "(status = 'failed' AND failure_code IS NOT NULL) OR "
            "(status <> 'failed' AND failure_code IS NULL)",
            name="ck_async_task_run_failure_code",
        ),
    )
    op.create_index("idx_async_task_run_resource", "async_task_runs", ["resource_type", "resource_id"])
    op.create_index("idx_async_task_run_status", "async_task_runs", ["status"])
    op.create_index(
        "idx_async_task_run_pending_dispatch",
        "async_task_runs",
        ["created_at"],
        postgresql_where=sa.text("status = 'queued' AND celery_task_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("async_task_runs")
    op.drop_table("candidate_documents")
    op.drop_table("candidate_profiles")
    op.drop_table("resumes")
    op.execute("DROP TRIGGER IF EXISTS trg_stored_file_objects_set_updated_at ON stored_file_objects")
    op.drop_table("stored_file_objects")
    op.execute("DROP TYPE IF EXISTS async_task_run_status_enum")
    op.execute("DROP TYPE IF EXISTS async_task_resource_type_enum")
    op.execute("DROP TYPE IF EXISTS async_task_type_enum")
    op.execute("DROP TYPE IF EXISTS document_type_enum")
    op.execute("DROP TYPE IF EXISTS parse_failure_code_enum")
    op.execute("DROP TYPE IF EXISTS parse_status_enum")
    op.execute("DROP TYPE IF EXISTS stored_file_object_status_enum")
