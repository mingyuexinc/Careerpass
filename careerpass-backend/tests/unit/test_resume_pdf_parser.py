"""Tests for deterministic embedded-text extraction from the fixed S-04 PDF."""

from pathlib import Path

from app.parsers.resume_pdf import (
    canonical_resume_text,
    compose_resume_extraction_source,
    extract_native_pdf_text,
)


def test_fixed_text_pdf_preserves_both_work_companies() -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures/candidate_preparation/resumes/resume_1.pdf"
    )

    text = extract_native_pdf_text(fixture.read_bytes())

    assert "成都天衍未来科技有限公司" in text
    assert "中兴通讯股份有限公司" in text


def test_composed_source_keeps_canonical_text_separate_from_mineru_context() -> None:
    source = compose_resume_extraction_source("Canonical Company", "MinerU Company")

    assert canonical_resume_text(source) == "Canonical Company"
