"""Deterministic filename-only CandidateDocument delivery matching."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.infrastructure.database.models import CandidateDocument, StoredFileObject

DocumentIntent = str

DOCUMENT_ALIASES: dict[DocumentIntent, tuple[str, ...]] = {
    "certificate": ("证书", "资格证", "认证", "certificate", "certification"),
    "photo": ("照片", "证件照", "photo", "picture"),
    "proof": ("证明", "证明材料", "proof", "document"),
}
REQUEST_MARKERS = (
    "请提供",
    "请发送",
    "能否提供",
    "可以提供",
    "请上传",
    "发一下",
    "发给我",
    "发来",
    "传一下",
    "传给我",
    "提供",
    "发送",
    "provide",
    "send",
    "share",
    "give me",
)
REQUESTED_NAME_PATTERNS = (
    re.compile(
        r"(?:把|将)\s*(?P<target>[^，。！？?!]+?)\s*"
        r"(?:发一下|发给我|发来|发送|提供|传一下|传给我|发)"
    ),
    re.compile(
        r"(?:请|麻烦|能否|可以)?\s*"
        r"(?:提供|发送|发一下|发给我|发来|传一下|传给我)\s*"
        r"(?P<target>[^，。！？?!]+)"
    ),
)


@dataclass(frozen=True)
class DocumentCandidate:
    document: CandidateDocument
    file_object: StoredFileObject


def normalize_document_text(value: str) -> str:
    """Normalize text for controlled semantic matching without reading file content."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"\.[a-z0-9]{1,8}$", "", normalized)
    normalized = re.sub(r"[_\-./\\]+", " ", normalized)
    normalized = re.sub(r"[^\w\u3400-\u9fff]+", " ", normalized)
    return " ".join(normalized.split())


def detect_document_intent(content: str) -> DocumentIntent | None:
    normalized = normalize_document_text(content)
    if not any(normalize_document_text(marker) in normalized for marker in REQUEST_MARKERS):
        return None
    for intent, aliases in DOCUMENT_ALIASES.items():
        if any(normalize_document_text(alias) in normalized for alias in aliases):
            return intent
    return extract_requested_document_name(content)


def extract_requested_document_name(content: str) -> str | None:
    """Extract a requested filename phrase without inspecting file contents."""
    normalized = normalize_document_text(content)
    for pattern in REQUESTED_NAME_PATTERNS:
        match = pattern.search(normalized)
        if match is None:
            continue
        target = re.sub(
            r"^(?:你的|我的|候选人的|求职者的|相关的|这份|该份|一份)\s*",
            "",
            match.group("target"),
        )
        target = target.strip()
        if target:
            return target
    return None


def resolve_document_candidates(
    *, intent: DocumentIntent, candidates: list[DocumentCandidate]
) -> DocumentCandidate | None:
    """Return one match only; ambiguity fails closed instead of guessing."""
    aliases = tuple(
        normalize_document_text(alias)
        for alias in DOCUMENT_ALIASES.get(intent, (intent,))
    )
    matches = [
        candidate
        for candidate in candidates
        if any(alias in normalize_document_text(candidate.document.document_name) for alias in aliases)
    ]
    return matches[0] if len(matches) == 1 else None


DOCUMENT_DELIVERY_REPLY = "已为你找到相关求职资料，请点击附件下载。"
DOCUMENT_UNAVAILABLE_REPLY = "暂时没有找到符合条件的求职资料。"
