"""Safe message projection tests for attachment-only Agent messages."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.services.conversation_service import _message_view, _proactive_response


def _message(*, sender: str, content: str, attachments: list[object]) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        sender=sender,
        message_type="text",
        status="sent",
        content=content,
        created_at=datetime.now(UTC),
        attachments=attachments,
    )


def _attachment() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        file_name="学籍验证报告.pdf",
        file_type="pdf",
        file_size_bytes=10,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        status="downloadable",
    )


def test_agent_attachment_projection_hides_legacy_success_prompt() -> None:
    view = _message_view(
        _message(
            sender="agent",
            content="已为你找到相关求职资料，请点击附件下载。",
            attachments=[_attachment()],
        )
    )

    assert view.content == ""
    assert len(view.attachments) == 1


def test_hr_message_content_is_preserved_even_with_an_attachment() -> None:
    view = _message_view(
        _message(sender="hr", content="请查收附件", attachments=[_attachment()])
    )

    assert view.content == "请查收附件"


def test_proactive_query_projection_does_not_lazy_load_attachments() -> None:
    class MessageWithoutAttachmentLoad:
        id = uuid4()
        sender = "agent"
        message_type = "text"
        status = "sent"
        content = "请确认一下，这个岗位是否属于外包岗位？"
        created_at = datetime.now(UTC)

        @property
        def attachments(self) -> list[object]:
            raise AssertionError("proactive query must not load attachments")

    turn = SimpleNamespace(
        id=uuid4(),
        scene="goal_query",
        status="waiting",
        outcome="query_sent",
        retryable=False,
    )
    response = _proactive_response(uuid4(), turn, MessageWithoutAttachmentLoad())

    assert response.new_messages[0].content == "请确认一下，这个岗位是否属于外包岗位？"
    assert response.new_messages[0].attachments == []
