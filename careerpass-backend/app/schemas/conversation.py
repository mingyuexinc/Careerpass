"""Safe S10-01 conversation contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MessageSender = Literal["hr", "agent"]
MessageStatus = Literal["pending", "sent", "failed"]
AgentTurnStatus = Literal["accepted", "processing", "waiting", "completed", "failed"]
AttachmentStatus = Literal["preparing", "downloadable", "failed", "expired"]


class MessageAttachmentView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    file_name: str
    file_type: str
    file_size_bytes: int
    created_at: datetime
    expires_at: datetime
    status: AttachmentStatus


class MessageView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    sender: MessageSender
    message_type: Literal["text"]
    status: MessageStatus
    content: str
    created_at: datetime
    attachments: list[MessageAttachmentView] = Field(default_factory=list)


class ConversationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    application_id: UUID
    job_title: str
    candidate_name: str
    messages: list[MessageView]


class ConversationListResponse(BaseModel):
    conversations: list[ConversationView]
    total: int


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    client_message_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=4000)


class AgentTurnView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    scene: Literal["resume_answer", "document_delivery", "goal_query", "goal_judgement"]
    turn_status: AgentTurnStatus
    outcome: Literal[
        "message_sent", "attachment_sent", "document_not_found", "attachment_failed", "tool_failed",
        "query_sent", "pending", "continue", "stop", "silent_end"
    ]
    retryable: bool


class SendMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    received_message: MessageView
    agent_turn: AgentTurnView
    new_messages: list[MessageView]


class StartProactiveQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID


class StartProactiveQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    agent_turn: AgentTurnView | None = None
    new_messages: list[MessageView] = Field(default_factory=list)
