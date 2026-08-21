"""S10-01 HR conversation and constrained Agent reply orchestration."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.infrastructure.qwen_communication import QwenCommunicationAdapter, QwenCommunicationError
from app.infrastructure.storage.local import LocalObjectStorage
from app.repositories.conversation_repository import (
    ConversationIdempotencyRaceError,
    ConversationRepository,
    ConversationViewRecord,
    resume_facts,
)
from app.schemas.communication import ResumeAnswerDraft
from app.schemas.conversation import (
    AgentTurnView,
    ConversationView,
    MessageAttachmentView,
    MessageView,
    SendMessageResponse,
    StartProactiveQueryResponse,
)
from app.schemas.job_description import ParsedJobDescriptionFields
from app.services.document_delivery_service import (
    DOCUMENT_DELIVERY_REPLY,
    DOCUMENT_UNAVAILABLE_REPLY,
    DocumentCandidate,
    detect_document_intent,
    resolve_document_candidates,
)
from app.services.s10_03_goal_communication import (
    GoalConditionGap,
    find_goal_condition_gap,
    parse_binary_answer,
)

FALLBACK_REPLY = "暂时无法从当前求职资料确认这个问题。"
NEGATIVE_TRAINING_REPLY = "从当前求职资料看，没有大模型训练相关经历。"
CONTINUE_REPLY = "好的，了解"
STOP_REPLY = "感谢沟通，当前不考虑这个岗位了"
_TRAINING_QUERY_TERMS = (
    "大模型训练",
    "模型训练",
    "大模型微调",
    "模型微调",
    "微调",
    "fine-tuning",
    "sft",
    "lora",
    "dpo",
    "强化学习",
)


class ConversationNotFoundError(Exception):
    """The current HR identity cannot access the requested conversation."""


class DocumentDeliveryError(Exception):
    """Attachment preparation failed without creating a visible partial message."""


class AttachmentExpiredError(Exception):
    """The requested attachment is outside its seven-day download window."""


@dataclass(frozen=True)
class DownloadableAttachment:
    content: bytes
    media_type: str
    file_name: str


class ConversationService:
    """Coordinate authorization, idempotency, Qwen validation and message writes."""

    def __init__(
        self,
        *,
        repository: ConversationRepository,
        responder: QwenCommunicationAdapter,
        storage: LocalObjectStorage | None = None,
    ) -> None:
        self._repository = repository
        self._responder = responder
        self._storage = storage

    async def list_current_for_hr(self, *, hr_profile_id: UUID) -> list[ConversationView]:
        async with self._repository.transaction():
            records = await self._repository.list_current_for_hr(hr_profile_id=hr_profile_id)
        return [_view(record) for record in records]

    async def get_messages_for_hr(
        self, *, application_id: UUID, conversation_id: UUID, hr_profile_id: UUID
    ) -> list[MessageView]:
        async with self._repository.transaction():
            context = await self._repository.get_for_hr(
                application_id=application_id,
                conversation_id=conversation_id,
                hr_profile_id=hr_profile_id,
            )
            if context is None:
                raise ConversationNotFoundError
            messages = await self._repository.list_messages(conversation_id=conversation_id)
        return [_message_view(message) for message in messages]

    async def start_proactive_query(
        self, *, application_id: UUID, conversation_id: UUID, hr_profile_id: UUID
    ) -> StartProactiveQueryResponse:
        """Idempotently start the single S10-03 question for a conversation."""
        async with self._repository.transaction():
            context = await self._repository.get_for_hr(
                application_id=application_id,
                conversation_id=conversation_id,
                hr_profile_id=hr_profile_id,
            )
            if context is None:
                raise ConversationNotFoundError
            gap = find_goal_condition_gap(context.job_goal, context.snapshot)
            if gap is None:
                return StartProactiveQueryResponse(conversation_id=conversation_id)
            key = f"s10-03:{application_id}:{conversation_id}:{gap.signature}"
            turn = await self._repository.get_turn_by_idempotency_key(idempotency_key=key)
            if turn is None:
                try:
                    turn = await self._repository.add_proactive_turn(
                        conversation_id=conversation_id, idempotency_key=key
                    )
                except ConversationIdempotencyRaceError:
                    turn = await self._repository.get_turn_by_idempotency_key(idempotency_key=key)
                    if turn is None:
                        raise
                if turn.status == "processing":
                    message = await self._repository.add_agent_message(
                        conversation_id=conversation_id,
                        content=gap.question,
                        turn=turn,
                        scene="goal_query",
                        outcome="query_sent",
                        status="waiting",
                    )
                else:
                    message = await self._repository.get_result_message_for_turn(turn=turn)
            else:
                message = await self._repository.get_result_message_for_turn(turn=turn)
            return _proactive_response(conversation_id, turn, message)

    async def download_attachment(
        self,
        *,
        application_id: UUID,
        message_id: UUID,
        attachment_id: UUID,
        hr_profile_id: UUID,
    ) -> DownloadableAttachment:
        expired = False
        async with self._repository.transaction():
            record = await self._repository.get_attachment_for_hr(
                application_id=application_id,
                message_id=message_id,
                attachment_id=attachment_id,
                hr_profile_id=hr_profile_id,
            )
            if record is None:
                raise ConversationNotFoundError
            now = datetime.now(UTC)
            if record.attachment.expires_at <= now:
                await self._repository.mark_attachment_expired(record.attachment)
                expired = True
            elif record.file_object is None or record.file_object.status != "ready":
                raise DocumentDeliveryError
            else:
                storage_key = record.file_object.storage_key
                media_type = record.file_object.detected_mime_type
                file_name = _safe_download_name(record.attachment.file_name)
                if self._storage is None:
                    raise DocumentDeliveryError
                try:
                    content = self._storage.read(storage_key)
                except (OSError, ValueError) as exc:
                    raise DocumentDeliveryError from exc
        if expired:
            raise AttachmentExpiredError
        return DownloadableAttachment(content=content, media_type=media_type, file_name=file_name)

    async def send_message(
        self,
        *,
        application_id: UUID,
        conversation_id: UUID,
        hr_profile_id: UUID,
        client_message_id: str,
        content: str,
    ) -> SendMessageResponse:
        pending_existing: tuple[object, object] | None = None
        pending_goal_turn = None
        goal_gap: GoalConditionGap | None = None
        document_intent = None
        candidate_id: UUID | None = None
        facts: dict[str, object] | None = None
        try:
            async with self._repository.transaction():
                context = await self._repository.get_for_hr(
                    application_id=application_id,
                    conversation_id=conversation_id,
                    hr_profile_id=hr_profile_id,
                )
                if context is None:
                    raise ConversationNotFoundError
                candidate_id = context.application.candidate_id
                existing = await self._repository.get_inbound_message(
                    conversation_id=conversation_id,
                    client_message_id=client_message_id,
                )
                if existing is not None:
                    turn = await self._repository.get_turn_for_message(source_message_id=existing.id)
                    if turn is None:
                        raise ConversationNotFoundError
                    if turn.status == "processing":
                        pending_existing = (existing, turn)
                    else:
                        result = await self._repository.get_result_message_for_turn(turn=turn)
                        return _send_response(
                            conversation_id,
                            existing,
                            turn,
                            [existing] + ([result] if result is not None else []),
                        )
                else:
                    pending_goal_turn = await self._repository.get_pending_goal_query(
                        conversation_id=conversation_id
                    )
                    goal_gap = find_goal_condition_gap(context.job_goal, context.snapshot)
                    document_intent = (
                        None
                        if pending_goal_turn is not None
                        else detect_document_intent(content)
                    )
                    inbound, turn = await self._repository.add_inbound_turn(
                        conversation_id=conversation_id,
                        client_message_id=client_message_id,
                        content=content,
                        idempotency_key=f"s10-01:{conversation_id}:{client_message_id}",
                        scene=(
                            "goal_judgement"
                            if pending_goal_turn is not None
                            else (
                                "document_delivery"
                                if document_intent is not None
                                else "resume_answer"
                            )
                        ),
                    )
                    if document_intent is None:
                        facts = resume_facts(context.profile)
        except ConversationIdempotencyRaceError:
            # A concurrent retry may win the unique client_message_id constraint
            # between the read and insert.  Re-read the committed original result.
            async with self._repository.transaction():
                existing = await self._repository.get_inbound_message(
                    conversation_id=conversation_id,
                    client_message_id=client_message_id,
                )
                if existing is None:
                    raise
                turn = await self._repository.get_turn_for_message(source_message_id=existing.id)
                if turn is None:
                    raise ConversationNotFoundError
                if turn.status == "processing":
                    pending_existing = (existing, turn)
                else:
                    result = await self._repository.get_result_message_for_turn(turn=turn)
                    return _send_response(
                        conversation_id,
                        existing,
                        turn,
                        [existing] + ([result] if result is not None else []),
                    )

        if pending_existing is not None:
            return await self._wait_for_existing_result(
                conversation_id=conversation_id,
                inbound=pending_existing[0],
                turn_id=pending_existing[1].id,
            )

        if pending_goal_turn is not None:
            return await self._judge_goal_answer(
                conversation_id=conversation_id,
                inbound=inbound,
                turn=turn,
                pending_query=pending_goal_turn,
                gap=goal_gap,
                content=content,
            )

        if document_intent is not None:
            if candidate_id is None:
                raise ConversationNotFoundError
            return await self._deliver_document(
                conversation_id=conversation_id,
                inbound=inbound,
                turn=turn,
                candidate_id=candidate_id,
                intent=document_intent,
            )

        failure_code: str | None = None
        try:
            if facts is None:
                raise ConversationNotFoundError
            draft = await self._responder.answer(question=content, facts=facts)
            reply = _validated_reply(draft, facts, question=content)
        except QwenCommunicationError as exc:
            failure_code = exc.failure_code
            reply = FALLBACK_REPLY
        except ValueError:
            failure_code = "schema_validation_failed"
            reply = FALLBACK_REPLY

        async with self._repository.transaction():
            current_turn = await self._repository.get_turn(turn_id=turn.id)
            if current_turn is None:
                raise ConversationNotFoundError
            if current_turn.status == "completed":
                result = await self._repository.get_result_message_for_turn(turn=current_turn)
                return _send_response(
                    conversation_id,
                    inbound,
                    current_turn,
                    [inbound] + ([result] if result is not None else []),
                )
            agent_message = await self._repository.add_agent_message(
                conversation_id=conversation_id,
                content=reply,
                turn=current_turn,
                failure_code=failure_code,
            )
            return _send_response(conversation_id, inbound, current_turn, [inbound, agent_message])

    async def _deliver_document(
        self,
        *,
        conversation_id: UUID,
        inbound: object,
        turn: object,
        candidate_id: UUID,
        intent: str,
    ) -> SendMessageResponse:
        try:
            async with self._repository.transaction():
                records = await self._repository.list_candidate_documents_for_delivery(
                    candidate_id=candidate_id
                )
                match = resolve_document_candidates(
                    intent=intent,  # type: ignore[arg-type]
                    candidates=[
                        DocumentCandidate(document=document, file_object=file_object)
                        for document, file_object in records
                    ],
                )
                current_turn = await self._repository.get_turn(turn_id=turn.id)
                if current_turn is None:
                    raise ConversationNotFoundError
                if current_turn.status == "completed":
                    result = await self._repository.get_result_message_for_turn(turn=current_turn)
                    return _send_response(
                        conversation_id,
                        inbound,
                        current_turn,
                        [inbound] + ([result] if result is not None else []),
                    )
                if match is None:
                    agent_message = await self._repository.add_agent_message(
                        conversation_id=conversation_id,
                        content=DOCUMENT_UNAVAILABLE_REPLY,
                        turn=current_turn,
                        scene="document_delivery",
                        outcome="document_not_found",
                    )
                    return _send_response(
                        conversation_id, inbound, current_turn, [inbound, agent_message]
                    )
                agent_message = await self._repository.add_agent_message(
                    conversation_id=conversation_id,
                    content=DOCUMENT_DELIVERY_REPLY,
                    turn=current_turn,
                    scene="document_delivery",
                    outcome="attachment_sent",
                )
                attachment = await self._repository.add_message_attachment(
                    message_id=agent_message.id,
                    candidate_document_id=match.document.id,
                    stored_file_object_id=match.file_object.id,
                    file_name=match.document.document_name,
                    file_type=match.document.file_type,
                    file_size_bytes=match.file_object.file_size_bytes,
                )
                return _send_response(
                    conversation_id,
                    inbound,
                    current_turn,
                    [inbound, agent_message],
                    {agent_message.id: [attachment]},
                )
        except ConversationNotFoundError:
            raise
        except Exception as exc:
            async with self._repository.transaction():
                current_turn = await self._repository.get_turn(turn_id=turn.id)
                if current_turn is not None and current_turn.status != "completed":
                    await self._repository.fail_turn(
                        turn=current_turn, failure_code="attachment_failed"
                    )
            raise DocumentDeliveryError from exc

    async def _wait_for_existing_result(
        self, *, conversation_id: UUID, inbound: object, turn_id: UUID
    ) -> SendMessageResponse:
        """Return the committed result when a concurrent retry sees processing."""
        for _ in range(40):
            async with self._repository.transaction():
                turn = await self._repository.get_turn(turn_id=turn_id)
                if turn is None:
                    raise ConversationNotFoundError
                if turn.status != "processing":
                    result = await self._repository.get_result_message_for_turn(turn=turn)
                    return _send_response(
                        conversation_id,
                        inbound,
                        turn,
                        [inbound] + ([result] if result is not None else []),
                    )
            await asyncio.sleep(0.05)
        raise ConversationNotFoundError

    async def _judge_goal_answer(
        self,
        *,
        conversation_id: UUID,
        inbound: object,
        turn: object,
        pending_query: object,
        gap: GoalConditionGap | None,
        content: str,
    ) -> SendMessageResponse:
        answer = parse_binary_answer(content)
        if gap is None or answer is None:
            async with self._repository.transaction():
                current_turn = await self._repository.get_turn(turn_id=turn.id)
                current_query = await self._repository.get_turn(turn_id=pending_query.id)
                if current_turn is None or current_query is None:
                    raise ConversationNotFoundError
                if current_turn.status != "completed":
                    await self._repository.complete_turn_without_message(
                        turn=current_turn, outcome="pending"
                    )
                    await self._repository.mark_turn_waiting(turn=current_query, outcome="pending")
                return _send_response(conversation_id, inbound, current_turn, [inbound])

        stop = answer.value == gap.stop_on_yes
        outcome = "stop" if stop else "continue"
        reply = STOP_REPLY if stop else CONTINUE_REPLY
        async with self._repository.transaction():
            current_turn = await self._repository.get_turn(turn_id=turn.id)
            current_query = await self._repository.get_turn(turn_id=pending_query.id)
            if current_turn is None or current_query is None:
                raise ConversationNotFoundError
            if current_turn.status == "completed":
                result = await self._repository.get_result_message_for_turn(turn=current_turn)
                return _send_response(
                    conversation_id,
                    inbound,
                    current_turn,
                    [inbound] + ([result] if result is not None else []),
                )
            agent_message = await self._repository.add_agent_message(
                conversation_id=conversation_id,
                content=reply,
                turn=current_turn,
                scene="goal_judgement",
                outcome=outcome,
            )
            await self._repository.complete_goal_query(turn=current_query, outcome=outcome)
            return _send_response(conversation_id, inbound, current_turn, [inbound, agent_message])


def _validated_reply(
    draft: ResumeAnswerDraft, facts: dict[str, object], *, question: str = ""
) -> str:
    if not draft.supported:
        if _can_answer_negative_training(question=question, facts=facts):
            return NEGATIVE_TRAINING_REPLY
        return FALLBACK_REPLY
    allowed = set(facts.get("skills", []))
    for group in (facts.get("work_experience", []), facts.get("project_experience", [])):
        if isinstance(group, list):
            for item in group:
                if isinstance(item, dict):
                    for key in ("name", "title", "company_name"):
                        if item.get(key):
                            allowed.add(item[key])
    if any(ref not in allowed for ref in draft.fact_refs):
        raise ValueError("answer fact reference is unsupported")
    return draft.answer.strip() or FALLBACK_REPLY


def _can_answer_negative_training(*, question: str, facts: dict[str, object]) -> bool:
    """Use a closed-world negative only when the structured experience scope is present."""
    if not any(term in question.casefold() for term in _TRAINING_QUERY_TERMS):
        return False
    if not any(marker in question for marker in ("有没有", "是否", "包括", "涉及", "做过", "参与过")):
        return False
    experience_groups = (facts.get("work_experience", []), facts.get("project_experience", []))
    if not any(isinstance(group, list) and any(isinstance(item, dict) and any(item.values() for item in group) for item in group) for group in experience_groups):
        return False
    supplied_experience = " ".join(
        str(value)
        for group in experience_groups
        if isinstance(group, list)
        for item in group
        if isinstance(item, dict)
        for value in item.values()
    ).casefold()
    return not any(term in supplied_experience for term in _TRAINING_QUERY_TERMS)


def _safe_download_name(file_name: str) -> str:
    value = re.sub(r"[\r\n\\/\x00]", "_", file_name).strip()
    return value or "attachment"


def _message_view(message: object, attachments: list[object] | None = None) -> MessageView:
    if attachments is None:
        attachments = list(getattr(message, "attachments", []))
    content = message.content
    if message.sender == "agent" and attachments:
        # Older successful deliveries may have persisted a prompt before the
        # S10-02 contract was tightened.  The attachment projection is the
        # only visible result for every successful delivery, including those
        # historical messages.
        content = ""
    return MessageView(
        id=message.id,
        sender=message.sender,
        message_type=message.message_type,
        status=message.status,
        content=content,
        created_at=message.created_at,
        attachments=[
            MessageAttachmentView.model_validate(item, from_attributes=True)
            for item in attachments
        ],
    )


def _turn_view(turn: object) -> AgentTurnView:
    return AgentTurnView(
        id=turn.id,
        scene=turn.scene,
        turn_status=turn.status,
        outcome=turn.outcome or "tool_failed",
        retryable=turn.retryable,
    )


def _send_response(
    conversation_id: UUID,
    inbound: object,
    turn: object,
    messages: list[object],
    attachments_by_message_id: dict[UUID, list[object]] | None = None,
) -> SendMessageResponse:
    attachment_map = attachments_by_message_id or {}
    return SendMessageResponse(
        conversation_id=conversation_id,
        received_message=_message_view(inbound, attachment_map.get(inbound.id, [])),
        agent_turn=_turn_view(turn),
        new_messages=[
            _message_view(message, attachment_map.get(message.id, [])) for message in messages
        ],
    )


def _proactive_response(
    conversation_id: UUID, turn: object, message: object | None
) -> StartProactiveQueryResponse:
    return StartProactiveQueryResponse(
        conversation_id=conversation_id,
        agent_turn=_turn_view(turn),
        # Proactive goal queries never create attachments.  Pass the empty
        # collection explicitly because the repository-created Message is
        # still in the current session and its relationship uses lazy="raise".
        new_messages=[] if message is None else [_message_view(message, [])],
    )


def _view(record: ConversationViewRecord) -> ConversationView:
    fields = ParsedJobDescriptionFields.model_validate(record.snapshot.fields)
    title = fields.title.normalized or fields.title.raw or record.job.file_name or "受控岗位"
    return ConversationView(
        id=record.conversation.id,
        application_id=record.application.id,
        job_title=title,
        candidate_name=record.profile.full_name or "候选人",
        messages=[_message_view(message) for message in record.messages],
    )
