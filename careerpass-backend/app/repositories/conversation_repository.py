"""Repository boundary for HR-scoped S10 conversations and messages."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.infrastructure.database.models import (
    AgentRunContext,
    AgentTurn,
    Application,
    CandidateDocument,
    CandidateProfile,
    Conversation,
    Job,
    JobGoal,
    Message,
    MessageAttachment,
    ParsedJobDescriptionSnapshot,
    StoredFileObject,
)


@dataclass(frozen=True)
class ConversationViewRecord:
    conversation: Conversation
    application: Application
    job: Job
    profile: CandidateProfile
    snapshot: ParsedJobDescriptionSnapshot
    messages: list[Message]


@dataclass(frozen=True)
class ConversationContext:
    conversation: Conversation
    application: Application
    profile: CandidateProfile
    job_goal: JobGoal | None = None
    snapshot: ParsedJobDescriptionSnapshot | None = None


@dataclass(frozen=True)
class AttachmentDownloadRecord:
    attachment: MessageAttachment
    file_object: StoredFileObject | None


class ConversationRepository:
    """Own S10 persistence, HR authorization, and safe message queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def transaction(self) -> AbstractAsyncContextManager[None]:
        return self._session.begin()

    async def list_current_for_hr(self, *, hr_profile_id: UUID) -> list[ConversationViewRecord]:
        run = AgentRunContext
        latest_run = aliased(AgentRunContext)
        latest_run_id = (
            select(latest_run.id)
            .order_by(desc(latest_run.created_at), desc(latest_run.id))
            .limit(1)
            .scalar_subquery()
        )
        rows = (
            await self._session.execute(
                select(Conversation, Application, Job, CandidateProfile, ParsedJobDescriptionSnapshot, Message)
                .join(Application, Application.id == Conversation.application_id)
                .join(Job, Job.id == Application.job_id)
                .join(run, run.id == Application.run_id)
                .join(CandidateProfile, CandidateProfile.id == run.candidate_profile_id)
                .join(ParsedJobDescriptionSnapshot, ParsedJobDescriptionSnapshot.job_id == Job.id)
                .outerjoin(Message, Message.conversation_id == Conversation.id)
                .where(
                    Job.hr_profile_id == hr_profile_id,
                    Job.deleted_at.is_(None),
                    run.id == latest_run_id,
                    Application.candidate_id == run.candidate_id,
                    CandidateProfile.resume_id == run.resume_id,
                )
                .options(selectinload(Message.attachments))
                .order_by(Job.created_at, Conversation.created_at, Message.created_at, Message.id)
            )
        ).all()
        grouped: dict[UUID, ConversationViewRecord] = {}
        for conversation, application, job, profile, snapshot, message in rows:
            current = grouped.get(conversation.id)
            if current is None:
                current = ConversationViewRecord(
                    conversation=conversation,
                    application=application,
                    job=job,
                    profile=profile,
                    snapshot=snapshot,
                    messages=[],
                )
                grouped[conversation.id] = current
            if message is not None:
                current.messages.append(message)
        return list(grouped.values())

    async def get_for_hr(
        self,
        *,
        application_id: UUID,
        conversation_id: UUID,
        hr_profile_id: UUID,
    ) -> ConversationContext | None:
        row = await self._session.execute(
            select(Conversation, Application, CandidateProfile)
            .join(Application, Application.id == Conversation.application_id)
            .join(Job, Job.id == Application.job_id)
            .join(AgentRunContext, AgentRunContext.id == Application.run_id)
            .join(CandidateProfile, CandidateProfile.id == AgentRunContext.candidate_profile_id)
            .where(
                Conversation.id == conversation_id,
                Conversation.application_id == application_id,
                Job.hr_profile_id == hr_profile_id,
                Job.deleted_at.is_(None),
                Application.candidate_id == AgentRunContext.candidate_id,
                CandidateProfile.resume_id == AgentRunContext.resume_id,
            )
            .with_for_update()
        )
        value = row.one_or_none()
        if value is None:
            return None
        conversation, application, profile = value
        job_goal = await self._session.scalar(
            select(JobGoal)
            .join(AgentRunContext, AgentRunContext.job_goal_id == JobGoal.id)
            .where(
                AgentRunContext.id == application.run_id,
                JobGoal.candidate_id == application.candidate_id,
            )
        )
        snapshot = await self._session.scalar(
            select(ParsedJobDescriptionSnapshot).where(
                ParsedJobDescriptionSnapshot.job_id == application.job_id,
            )
        )
        return ConversationContext(
            conversation=conversation,
            application=application,
            profile=profile,
            job_goal=job_goal,
            snapshot=snapshot,
        )

    async def list_messages(self, *, conversation_id: UUID) -> list[Message]:
        result = await self._session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(selectinload(Message.attachments))
            .order_by(Message.created_at, Message.id)
        )
        return list(result)

    async def get_inbound_message(
        self, *, conversation_id: UUID, client_message_id: str
    ) -> Message | None:
        return await self._session.scalar(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.sender == "hr",
                Message.client_message_id == client_message_id,
            )
        )

    async def get_turn_for_message(self, *, source_message_id: UUID) -> AgentTurn | None:
        return await self._session.scalar(
            select(AgentTurn).where(AgentTurn.source_message_id == source_message_id)
        )

    async def get_turn(self, *, turn_id: UUID) -> AgentTurn | None:
        return await self._session.scalar(
            select(AgentTurn)
            .where(AgentTurn.id == turn_id)
            .execution_options(populate_existing=True)
        )

    async def get_turn_by_idempotency_key(self, *, idempotency_key: str) -> AgentTurn | None:
        return await self._session.scalar(
            select(AgentTurn).where(AgentTurn.idempotency_key == idempotency_key)
        )

    async def get_pending_goal_query(self, *, conversation_id: UUID) -> AgentTurn | None:
        return await self._session.scalar(
            select(AgentTurn)
            .where(
                AgentTurn.conversation_id == conversation_id,
                AgentTurn.scene == "goal_query",
                AgentTurn.status == "waiting",
            )
            .order_by(desc(AgentTurn.created_at), desc(AgentTurn.id))
            .limit(1)
            .with_for_update()
        )

    async def get_result_message_for_turn(self, *, turn: AgentTurn) -> Message | None:
        if turn.result_message_id is not None:
            return await self._session.scalar(
                select(Message)
                .where(Message.id == turn.result_message_id)
                .options(selectinload(Message.attachments))
            )
        if turn.source_message_id is None:
            return None
        return await self.get_result_message(source_message_id=turn.source_message_id)

    async def get_result_message(self, *, source_message_id: UUID) -> Message | None:
        source = await self._session.get(Message, source_message_id)
        if source is None:
            return None
        return await self._session.scalar(
            select(Message)
            .where(
                Message.conversation_id == source.conversation_id,
                Message.sender == "agent",
                Message.created_at >= source.created_at,
            )
            .options(selectinload(Message.attachments))
            .order_by(Message.created_at, Message.id)
            .limit(1)
        )

    async def list_candidate_documents_for_delivery(
        self, *, candidate_id: UUID
    ) -> list[tuple[CandidateDocument, StoredFileObject]]:
        result = await self._session.execute(
            select(CandidateDocument, StoredFileObject)
            .join(
                StoredFileObject,
                CandidateDocument.stored_file_object_id == StoredFileObject.id,
            )
            .where(
                CandidateDocument.candidate_id == candidate_id,
                CandidateDocument.deleted_at.is_(None),
                StoredFileObject.status == "ready",
            )
            .order_by(CandidateDocument.created_at, CandidateDocument.id)
        )
        return list(result.all())

    async def get_attachment_for_hr(
        self,
        *,
        application_id: UUID,
        message_id: UUID,
        attachment_id: UUID,
        hr_profile_id: UUID,
    ) -> AttachmentDownloadRecord | None:
        row = await self._session.execute(
            select(MessageAttachment, StoredFileObject)
            .join(Message, Message.id == MessageAttachment.message_id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .join(Application, Application.id == Conversation.application_id)
            .join(Job, Job.id == Application.job_id)
            .join(AgentRunContext, AgentRunContext.id == Application.run_id)
            .outerjoin(StoredFileObject, StoredFileObject.id == MessageAttachment.stored_file_object_id)
            .where(
                MessageAttachment.id == attachment_id,
                MessageAttachment.message_id == message_id,
                Message.sender == "agent",
                Conversation.application_id == application_id,
                Job.hr_profile_id == hr_profile_id,
                Job.deleted_at.is_(None),
                Application.candidate_id == AgentRunContext.candidate_id,
            )
            .with_for_update(of=MessageAttachment)
        )
        value = row.one_or_none()
        if value is None:
            return None
        attachment, file_object = value
        return AttachmentDownloadRecord(attachment=attachment, file_object=file_object)

    async def add_inbound_turn(
        self,
        *,
        conversation_id: UUID,
        client_message_id: str,
        content: str,
        idempotency_key: str,
        scene: str = "resume_answer",
    ) -> tuple[Message, AgentTurn]:
        now = datetime.now(UTC)
        message = Message(
            conversation_id=conversation_id,
            sender="hr",
            message_type="text",
            status="sent",
            content=content,
            client_message_id=client_message_id,
            created_at=now,
        )
        self._session.add(message)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConversationIdempotencyRaceError from exc
        turn = AgentTurn(
            conversation_id=conversation_id,
            source_message_id=message.id,
            idempotency_key=idempotency_key,
            scene=scene,
            status="processing",
            created_at=now,
            updated_at=now,
        )
        self._session.add(turn)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConversationIdempotencyRaceError from exc
        return message, turn

    async def add_proactive_turn(
        self, *, conversation_id: UUID, idempotency_key: str
    ) -> AgentTurn:
        now = datetime.now(UTC)
        turn = AgentTurn(
            conversation_id=conversation_id,
            source_message_id=None,
            idempotency_key=idempotency_key,
            scene="goal_query",
            status="processing",
            created_at=now,
            updated_at=now,
        )
        self._session.add(turn)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConversationIdempotencyRaceError from exc
        return turn

    async def add_agent_message(
        self,
        *,
        conversation_id: UUID,
        content: str,
        turn: AgentTurn,
        failure_code: str | None = None,
        outcome: str = "message_sent",
        scene: str = "resume_answer",
        status: str = "completed",
    ) -> Message:
        now = datetime.now(UTC)
        message = Message(
            conversation_id=conversation_id,
            sender="agent",
            message_type="text",
            status="sent",
            content=content,
            created_at=now,
        )
        self._session.add(message)
        turn.status = status
        turn.scene = scene
        turn.outcome = outcome
        turn.retryable = False
        turn.failure_code = failure_code
        turn.updated_at = now
        await self._session.flush()
        turn.result_message_id = message.id
        await self._session.flush()
        return message

    async def mark_turn_waiting(self, *, turn: AgentTurn, outcome: str = "query_sent") -> None:
        turn.status = "waiting"
        turn.outcome = outcome
        turn.retryable = False
        turn.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def complete_goal_query(self, *, turn: AgentTurn, outcome: str) -> None:
        turn.status = "completed"
        turn.outcome = outcome
        turn.retryable = False
        turn.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def complete_turn_without_message(self, *, turn: AgentTurn, outcome: str) -> None:
        turn.status = "completed"
        turn.outcome = outcome
        turn.retryable = False
        turn.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def add_message_attachment(
        self,
        *,
        message_id: UUID,
        candidate_document_id: UUID,
        stored_file_object_id: UUID,
        file_name: str,
        file_type: str,
        file_size_bytes: int,
    ) -> MessageAttachment:
        now = datetime.now(UTC)
        attachment = MessageAttachment(
            message_id=message_id,
            candidate_document_id=candidate_document_id,
            stored_file_object_id=stored_file_object_id,
            file_name=file_name,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            created_at=now,
            expires_at=now + timedelta(days=7),
            status="downloadable",
        )
        self._session.add(attachment)
        await self._session.flush()
        return attachment

    async def mark_attachment_expired(self, attachment: MessageAttachment) -> None:
        attachment.status = "expired"
        await self._session.flush()

    async def fail_turn(self, *, turn: AgentTurn, failure_code: str) -> None:
        now = datetime.now(UTC)
        turn.status = "failed"
        turn.outcome = "attachment_failed"
        turn.retryable = True
        turn.failure_code = failure_code
        turn.updated_at = now
        await self._session.flush()


class ConversationIdempotencyRaceError(Exception):
    """A concurrent request won the unique inbound-message constraint."""


def resume_facts(profile: CandidateProfile) -> dict[str, Any]:
    """Build the smallest validated, structured fact projection for Qwen."""
    return {
        "education": profile.education,
        "skills": [item.get("name") for item in profile.skills or [] if item.get("name")],
        "work_experience": profile.work_experience_summary or [],
        "project_experience": profile.project_experience_summary or [],
    }
