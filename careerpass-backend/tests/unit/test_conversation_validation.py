"""Deterministic S10-01 answer and visibility rules."""

import pytest

from app.schemas.communication import ResumeAnswerDraft
from app.services.conversation_service import (
    FALLBACK_REPLY,
    NEGATIVE_TRAINING_REPLY,
    _validated_reply,
)

FACTS = {
    "skills": ["Python"],
    "work_experience": [{"title": "后端工程师", "company_name": "示例公司"}],
    "project_experience": [{"name": "招聘助手"}],
}


def test_supported_answer_must_reference_supplied_facts() -> None:
    draft = ResumeAnswerDraft(supported=True, answer="候选人使用过 Python。", fact_refs=["Python"])
    assert _validated_reply(draft, FACTS) == "候选人使用过 Python。"


def test_unsupported_answer_uses_controlled_template() -> None:
    draft = ResumeAnswerDraft(supported=False, answer="无法确认", fact_refs=[])
    assert _validated_reply(draft, FACTS) == FALLBACK_REPLY


def test_absent_training_experience_returns_negative_answer() -> None:
    draft = ResumeAnswerDraft(supported=False, answer="无法确认", fact_refs=[])
    assert _validated_reply(
        draft,
        FACTS,
        question="你的工作经历中有包括大模型训练吗？",
    ) == NEGATIVE_TRAINING_REPLY


def test_absent_training_with_empty_experience_scope_stays_unknown() -> None:
    draft = ResumeAnswerDraft(supported=False, answer="无法确认", fact_refs=[])
    assert _validated_reply(
        draft,
        {"skills": [], "work_experience": [], "project_experience": []},
        question="你的工作经历中有包括大模型训练吗？",
    ) == FALLBACK_REPLY


def test_unknown_fact_reference_is_rejected() -> None:
    draft = ResumeAnswerDraft(supported=True, answer="候选人熟悉 Rust。", fact_refs=["Rust"])
    with pytest.raises(ValueError):
        _validated_reply(draft, FACTS)
