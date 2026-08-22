"""Deterministic S10-02 acceptance checks independent of Qwen."""

from pathlib import Path

import pytest

from app.services.document_delivery_service import (
    detect_document_intent,
    normalize_document_text,
    resolve_document_candidates,
)

pytestmark = pytest.mark.capability_acceptance


class _Candidate:
    def __init__(self, name: str) -> None:
        self.document = type("Document", (), {"document_name": name})()
        self.file_object = type("FileObject", (), {"id": name})()


@pytest.mark.parametrize(
    ("message", "intent", "file_name"),
    [
        ("请提供候选人的证书", "certificate", "candidate_certificate.pdf"),
        ("请发送候选人的照片", "photo", "candidate_photo.jpg"),
        ("请提供候选人的证明材料", "proof", "candidate_proof.png"),
        ("请把你的学籍验证报告发一下。", "academic_status", "学籍验证报告.pdf"),
    ],
)
def test_filename_semantic_fixture_matches_one_file(message: str, intent: str, file_name: str) -> None:
    assert detect_document_intent(message) == intent
    assert normalize_document_text(file_name)
    match = resolve_document_candidates(intent=intent, candidates=[_Candidate(file_name)])
    assert match is not None


def test_capability_fixture_fails_closed_on_multiple_matches() -> None:
    assert resolve_document_candidates(
        intent="certificate",
        candidates=[_Candidate("certificate-a.pdf"), _Candidate("certificate-b.pdf")],
    ) is None


def test_real_student_status_fixture_is_matched_by_filename_only() -> None:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "fixtures"
        / "candidate_preparation"
        / "candidate_documents"
        / "学籍验证报告.pdf"
    )
    assert fixture.is_file()
    assert detect_document_intent("请把你的学籍验证报告发一下。") == "academic_status"
    assert resolve_document_candidates(
        intent="academic_status",
        candidates=[_Candidate(fixture.name)],
    ) is not None


@pytest.mark.parametrize(
    "message",
    [
        "将你的学籍证明材料发一下",
        "请发送你的学籍材料",
        "将你的学籍验证报告材料发一下",
    ],
)
def test_academic_status_aliases_match_the_controlled_fixture(message: str) -> None:
    fixture_name = "学籍验证报告.pdf"
    intent = detect_document_intent(message)
    assert intent == "academic_status"
    assert resolve_document_candidates(
        intent=intent,
        candidates=[_Candidate(fixture_name)],
    ) is not None
