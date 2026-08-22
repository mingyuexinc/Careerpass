"""Deterministic S10-02 filename matching tests."""

from types import SimpleNamespace

from app.services.document_delivery_service import (
    detect_document_intent,
    normalize_document_text,
    resolve_document_candidates,
)


def _candidate(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        document=SimpleNamespace(document_name=name),
        file_object=SimpleNamespace(id=name),
    )


def test_normalization_ignores_extension_punctuation_and_case() -> None:
    assert normalize_document_text("Candidate_Certificate.PDF") == "candidate certificate"


def test_detects_supported_document_request_intents() -> None:
    assert detect_document_intent("请提供候选人的证书") == "certificate"
    assert detect_document_intent("Can you provide the candidate photo?") == "photo"
    assert detect_document_intent("请发送证明材料") == "proof"
    assert detect_document_intent("请把你的学籍验证报告发一下。") == "academic_status"


def test_detects_academic_status_aliases_and_matches_report_filename() -> None:
    messages = (
        "将你的学籍证明发一下",
        "请发送你的学籍材料",
        "将你的学籍验证报告材料发一下",
        "请把你的学籍验证报告发一下",
    )

    for message in messages:
        intent = detect_document_intent(message)
        assert intent == "academic_status"
        assert resolve_document_candidates(
            intent=intent,
            candidates=[_candidate("学籍验证报告.pdf")],
        ) is not None


def test_requires_request_language_and_does_not_read_file_content() -> None:
    assert detect_document_intent("证书") is None
    assert detect_document_intent("请介绍候选人的项目") is None


def test_resolves_one_filename_match_and_fails_closed_on_multiple_matches() -> None:
    assert resolve_document_candidates(
        intent="certificate",
        candidates=[_candidate("candidate_certificate.pdf")],
    ) is not None
    assert resolve_document_candidates(
        intent="certificate",
        candidates=[_candidate("certificate_a.pdf"), _candidate("certificate_b.pdf")],
    ) is None
    assert resolve_document_candidates(
        intent="academic_status",
        candidates=[_candidate("学籍验证报告.pdf")],
    ) is not None
