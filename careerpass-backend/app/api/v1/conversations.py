"""Authenticated HR-facing S10-01 conversation endpoints."""

from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.dependencies.auth import get_current_identity
from app.api.dependencies.services import get_conversation_service
from app.core.errors import ErrorCode
from app.core.exceptions import AppException
from app.core.identity import CurrentIdentity
from app.schemas.conversation import SendMessageRequest
from app.schemas.response import success_response
from app.services.conversation_service import (
    AttachmentExpiredError,
    ConversationNotFoundError,
    ConversationService,
    DocumentDeliveryError,
)

conversations_router = APIRouter(tags=["conversations"])


def _hr_profile_id(identity: CurrentIdentity) -> UUID:
    if identity.active_role != "hr" or identity.hr_profile_id is None:
        raise AppException(status_code=403, code=ErrorCode.FORBIDDEN, message="HR identity required")
    return identity.hr_profile_id


@conversations_router.get("/applications/hr/current/conversations")
async def list_current_conversations(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict[str, object]:
    conversations = await service.list_current_for_hr(hr_profile_id=_hr_profile_id(identity))
    return success_response(
        {"conversations": [item.model_dump(mode="json") for item in conversations], "total": len(conversations)}
    )


@conversations_router.get("/applications/{application_id}/conversation/messages")
async def list_conversation_messages(
    application_id: UUID,
    conversation_id: UUID,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict[str, object]:
    try:
        messages = await service.get_messages_for_hr(
            application_id=application_id,
            conversation_id=conversation_id,
            hr_profile_id=_hr_profile_id(identity),
        )
    except ConversationNotFoundError:
        raise AppException(status_code=404, code=ErrorCode.NOT_FOUND, message="conversation not found") from None
    return success_response({"messages": [item.model_dump(mode="json") for item in messages]})


@conversations_router.post("/applications/{application_id}/conversation/messages")
async def send_conversation_message(
    application_id: UUID,
    value: SendMessageRequest,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict[str, object]:
    try:
        result = await service.send_message(
            application_id=application_id,
            conversation_id=value.conversation_id,
            hr_profile_id=_hr_profile_id(identity),
            client_message_id=value.client_message_id,
            content=value.content.strip(),
        )
    except ConversationNotFoundError:
        raise AppException(status_code=404, code=ErrorCode.NOT_FOUND, message="conversation not found") from None
    except DocumentDeliveryError:
        raise AppException(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="attachment delivery unavailable",
        ) from None
    return success_response(result.model_dump(mode="json"))


@conversations_router.get(
    "/applications/{application_id}/conversation/messages/{message_id}/attachments/{attachment_id}/download"
)
async def download_conversation_attachment(
    application_id: UUID,
    message_id: UUID,
    attachment_id: UUID,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Response:
    try:
        attachment = await service.download_attachment(
            application_id=application_id,
            message_id=message_id,
            attachment_id=attachment_id,
            hr_profile_id=_hr_profile_id(identity),
        )
    except ConversationNotFoundError:
        raise AppException(status_code=404, code=ErrorCode.NOT_FOUND, message="attachment not found") from None
    except AttachmentExpiredError:
        raise AppException(status_code=410, code=ErrorCode.GONE, message="attachment expired") from None
    except DocumentDeliveryError:
        raise AppException(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="attachment unavailable",
        ) from None
    return Response(
        content=attachment.content,
        media_type=attachment.media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.file_name)}",
            "Content-Length": str(len(attachment.content)),
        },
    )
