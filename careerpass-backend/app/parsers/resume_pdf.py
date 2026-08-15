"""Deterministic text extraction for the text-PDF scope of S-04."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

_CANONICAL_START = "<!-- careerpass:canonical-pdf-text:start -->"
_CANONICAL_END = "<!-- careerpass:canonical-pdf-text:end -->"


def extract_native_pdf_text(pdf_content: bytes) -> str:
    """Extract embedded text without OCR; encrypted or empty PDFs remain unsupported."""
    reader = PdfReader(BytesIO(pdf_content))
    if reader.is_encrypted:
        raise ValueError("encrypted PDF is unsupported")
    pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    text = "\n\n".join(page.strip() for page in pages if page.strip()).strip()
    if not text:
        raise ValueError("PDF contains no embedded text")
    return text


def compose_resume_extraction_source(native_text: str, mineru_markdown: str) -> str:
    """Keep canonical text identifiable in memory while retaining MinerU layout context."""
    return (
        f"{_CANONICAL_START}\n{native_text}\n{_CANONICAL_END}\n\n"
        "<!-- careerpass:mineru-markdown:start -->\n"
        f"{mineru_markdown}\n"
        "<!-- careerpass:mineru-markdown:end -->"
    )


def canonical_resume_text(extraction_source: str) -> str:
    """Return the deterministic source used for field grounding."""
    start = extraction_source.find(_CANONICAL_START)
    end = extraction_source.find(_CANONICAL_END)
    if start < 0 or end <= start:
        return extraction_source
    return extraction_source[start + len(_CANONICAL_START) : end].strip()
