"""ORM models for MVP Lite identity and candidate ownership."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

STORED_FILE_OBJECT_STATUS = postgresql.ENUM(
    "writing", "ready", "deleting", name="stored_file_object_status_enum", create_type=False
)
PARSE_STATUS = postgresql.ENUM(
    "processing", "succeeded", "failed", name="parse_status_enum", create_type=False
)
PARSE_FAILURE_CODE = postgresql.ENUM(
    "unsupported_file", "file_unreadable", "storage_unavailable", "parser_timeout",
    "schema_validation_failed", "internal_error", name="parse_failure_code_enum", create_type=False,
)
DOCUMENT_TYPE = postgresql.ENUM(
    "certificate", "strategy", "other", name="document_type_enum", create_type=False
)
ASYNC_TASK_TYPE = postgresql.ENUM(
    "resume_parse", "job_jd_parse", name="async_task_type_enum", create_type=False
)
ASYNC_RESOURCE_TYPE = postgresql.ENUM(
    "resume", "job", name="async_task_resource_type_enum", create_type=False
)
ASYNC_TASK_STATUS = postgresql.ENUM(
    "queued", "running", "succeeded", "failed", name="async_task_run_status_enum", create_type=False
)

USER_ROLE = postgresql.ENUM("candidate", "hr", name="user_role_enum", create_type=False)

if TYPE_CHECKING:
    from app.infrastructure.database.models import Candidate, HrProfile, UserRole


class User(Base):
    """Credential-bearing account; password hashes must never leave the repository boundary."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    candidate: Mapped[Candidate | None] = relationship(
        back_populates="user",
        uselist=False,
        lazy="raise",
    )
    hr_profile: Mapped[HrProfile | None] = relationship(
        back_populates="user",
        uselist=False,
        lazy="raise",
    )
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        lazy="raise",
        cascade="all, delete-orphan",
    )


class Candidate(Base):
    """Candidate identity associated one-to-one with a user account."""

    __tablename__ = "candidates"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_candidate_user"),
        nullable=False,
        unique=True,
    )
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    user: Mapped[User] = relationship(back_populates="candidate", lazy="raise")


class JobGoal(Base):
    """Candidate-owned current job goal configured before Agent startup."""

    __tablename__ = "job_goals"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    offer_target: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    filters: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'active'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class AgentRunContext(Base):
    """Candidate-owned immutable startup context handed to downstream Agent slices."""

    __tablename__ = "agent_run_contexts"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_goal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("job_goals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resume_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_profile_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    goal_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'running'")
    )
    finish_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class HrProfile(Base):
    """HR business identity associated one-to-one with a user account."""

    __tablename__ = "hr_profiles"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_hr_profile_user"),
        nullable=False,
        unique=True,
    )
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    user: Mapped[User] = relationship(back_populates="hr_profile", lazy="raise")


class Job(Base):
    """HR-owned job created from one uploaded JD file."""

    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    hr_profile_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("hr_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stored_file_object_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("stored_file_objects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class UserRole(Base):
    """Role membership used to validate the active login workspace."""

    __tablename__ = "user_roles"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(USER_ROLE, nullable=False)
    user: Mapped[User] = relationship(back_populates="roles", lazy="raise")


class StoredFileObject(Base):
    """Internal, de-duplicated file object. Its location never crosses the API boundary."""

    __tablename__ = "stored_file_objects"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    detected_mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        STORED_FILE_OBJECT_STATUS, nullable=False, server_default=text("'writing'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Resume(Base):
    """Candidate-owned resume; parsing fields are owned by document parsing."""

    __tablename__ = "resumes"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    upload_idempotency_key: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_file_object_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("stored_file_objects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parse_status: Mapped[str] = mapped_column(
        PARSE_STATUS, nullable=False, server_default=text("'processing'")
    )
    failure_code: Mapped[str | None] = mapped_column(PARSE_FAILURE_CODE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class CandidateProfile(Base):
    """Validated deterministic facts derived from one successfully parsed resume."""

    __tablename__ = "candidate_profiles"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resume_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    matching_readiness: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'matching_not_ready'")
    )
    target_job_titles: Mapped[list[str]] = mapped_column(
        ARRAY(String(128)), nullable=False, server_default=text("ARRAY[]::varchar[]")
    )
    skills: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB, nullable=True)
    work_experience_summary: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSONB, nullable=True
    )
    project_experience_summary: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSONB, nullable=True
    )
    years_of_experience: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'unknown'")
    )
    education: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_salary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class CandidateDocument(Base):
    """Candidate-owned raw attachment; it intentionally has no parsing state."""

    __tablename__ = "candidate_documents"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    upload_idempotency_key: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    document_type: Mapped[str] = mapped_column(DOCUMENT_TYPE, nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    stored_file_object_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("stored_file_objects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class AsyncTaskRun(Base):
    """Persistent authoritative state for at-least-once parsing work."""

    __tablename__ = "async_task_runs"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_type: Mapped[str] = mapped_column(ASYNC_TASK_TYPE, nullable=False)
    resource_type: Mapped[str] = mapped_column(ASYNC_RESOURCE_TYPE, nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        ASYNC_TASK_STATUS, nullable=False, server_default=text("'queued'")
    )
    task_version: Mapped[str] = mapped_column(
        String(128), nullable=False, server_default=text("'v1'")
    )
    task_generation: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    dispatch_token: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    dispatch_lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(PARSE_FAILURE_CODE, nullable=True)
    failure_semantics: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    missing_core_fields: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_token: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    execution_lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class ParsedJobDescriptionSnapshot(Base):
    """Validated, deterministic JD fields consumed by downstream matching."""

    __tablename__ = "parsed_job_description_snapshots"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    job_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fields: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    raw_sections: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Match(Base):
    """One immutable v0.1 evaluation for one job in one Agent run."""

    __tablename__ = "matches"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("agent_run_contexts.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False
    )
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    role_score: Mapped[float | None] = mapped_column(nullable=True)
    level_score: Mapped[float | None] = mapped_column(nullable=True)
    skill_score: Mapped[float | None] = mapped_column(nullable=True)
    total_score: Mapped[float | None] = mapped_column(nullable=True)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Application(Base):
    """System-side application record created from a matched job."""

    __tablename__ = "applications"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("agent_run_contexts.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'submitted'"))
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Conversation(Base):
    """One current system conversation for an Application."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Message(Base):
    """A visible HR or Agent message in a Conversation."""

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender: Mapped[str] = mapped_column(String(16), nullable=False)
    message_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'text'"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'sent'"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    client_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attachments: Mapped[list["MessageAttachment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class MessageAttachment(Base):
    """Safe downloadable projection of one CandidateDocument in a Message."""

    __tablename__ = "message_attachments"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    message_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    candidate_document_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidate_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    stored_file_object_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("stored_file_objects.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'preparing'")
    )
    message: Mapped[Message] = relationship(back_populates="attachments", lazy="raise")


class AgentTurn(Base):
    """Idempotent execution record for one S10 HR message."""

    __tablename__ = "agent_turns"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()" )
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_message_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    scene: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'resume_answer'"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'accepted'"))
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retryable: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class ProgressEvent(Base):
    """Auditable state transition event for an Application."""

    __tablename__ = "progress_events"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
