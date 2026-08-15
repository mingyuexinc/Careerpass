"""Deterministic Markdown parser for the controlled S-03 JD format."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.job_description import (
    ExtraField,
    ParsedJobDescriptionFields,
    SalaryField,
    SectionField,
    SectionItem,
    TextField,
)

CORE_FIELDS = ("title", "location", "salary_range", "responsibilities", "requirements")

_HEADING_MAP = {
    "岗位名称": "title",
    "职位名称": "title",
    "标题": "title",
    "公司名称": "company_name",
    "公司": "company_name",
    "工作地点": "location",
    "地点": "location",
    "薪资": "salary_range",
    "薪资范围": "salary_range",
    "岗位性质": "job_nature",
    "用工类型": "employment_type",
    "面试方式": "interview_mode",
    "岗位摘要": "summary",
    "摘要": "summary",
    "岗位职责": "responsibilities",
    "职责": "responsibilities",
    "任职要求": "requirements",
    "岗位要求": "requirements",
    "要求": "requirements",
}
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+?)\s*$")
_SALARY_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[kK万])")


@dataclass(frozen=True)
class MarkdownSection:
    heading: str
    raw: str
    items: tuple[str, ...]
    source_order: int


class JobDescriptionParseError(ValueError):
    """The content is valid text but cannot produce a complete S-03 result."""

    def __init__(self, missing_core_fields: list[str]) -> None:
        self.missing_core_fields = missing_core_fields
        super().__init__("core fields missing")


def parse_job_description(content: bytes) -> tuple[ParsedJobDescriptionFields, list[dict[str, object]]]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JobDescriptionParseError(["input_unavailable"]) from exc
    sections = _sections(text)
    by_field = {_HEADING_MAP.get(section.heading): section for section in sections}
    implicit_title = (
        sections[0]
        if sections and sections[0].source_order == 0 and not sections[0].raw
        else None
    )
    if by_field.get("title") is None and implicit_title is not None:
        by_field["title"] = implicit_title
    missing = [field for field in CORE_FIELDS if by_field.get(field) is None]
    if missing:
        raise JobDescriptionParseError(missing)

    fields: dict[str, object] = {}
    additional: dict[str, ExtraField] = {}
    for section in sections:
        field_name = _HEADING_MAP.get(section.heading)
        if section is implicit_title and field_name is None:
            field_name = "title"
        if field_name == "salary_range":
            fields[field_name] = _salary_field(section)
        elif field_name in {"responsibilities", "requirements"}:
            fields[field_name] = _section_field(section)
        elif field_name in {"title", "company_name", "location", "job_nature", "employment_type", "interview_mode", "summary"}:
            fields[field_name] = _text_field(section)
        elif field_name is None:
            additional[section.heading] = _extra_field(section)
    fields["additional_fields"] = additional
    validated = ParsedJobDescriptionFields.model_validate(fields)
    raw_sections = [
        {
            "heading": section.heading,
            "raw": section.raw or (section.heading if section is implicit_title else ""),
            "items": list(section.items),
            "source_order": section.source_order,
        }
        for section in sections
    ]
    return validated, raw_sections


def _sections(text: str) -> list[MarkdownSection]:
    sections: list[MarkdownSection] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    order = 0
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if current_heading is not None:
                sections.append(_make_section(current_heading, current_lines, order))
                order += 1
            current_heading = match.group(1).strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line.rstrip())
    if current_heading is not None:
        sections.append(_make_section(current_heading, current_lines, order))
    return sections


def _make_section(heading: str, lines: list[str], source_order: int) -> MarkdownSection:
    meaningful = [line.strip() for line in lines if line.strip()]
    items = tuple(match.group(1).strip() for line in meaningful if (match := _BULLET_RE.match(line)))
    return MarkdownSection(heading, "\n".join(meaningful), items, source_order)


def _text_field(section: MarkdownSection) -> TextField:
    raw = section.raw or section.heading
    return TextField(
        raw=raw,
        normalized=raw.strip() or None,
        source_heading=section.heading,
        source_order=section.source_order,
    )


def _section_field(section: MarkdownSection) -> SectionField:
    return SectionField(
        raw=section.raw,
        items=[
            SectionItem(raw=item, normalized=item.strip(), source_order=index)
            for index, item in enumerate(section.items)
        ],
        source_heading=section.heading,
        source_order=section.source_order,
    )


def _extra_field(section: MarkdownSection) -> ExtraField:
    return ExtraField(
        raw=section.raw,
        normalized=section.raw.strip() or None,
        items=[
            SectionItem(raw=item, normalized=item.strip(), source_order=index)
            for index, item in enumerate(section.items)
        ] or None,
        source_heading=section.heading,
        source_order=section.source_order,
    )


def _salary_field(section: MarkdownSection) -> SalaryField:
    values: list[float] = []
    for match in _SALARY_RE.finditer(section.raw):
        value = float(match.group("value"))
        unit = match.group("unit").lower()
        if unit == "k":
            value *= 1000
        elif unit == "万":
            value *= 10000
        values.append(value)
    period = None
    if re.search(r"月|月薪|/月", section.raw):
        period = "month"
    elif re.search(r"年|年薪|/年", section.raw):
        period = "year"
    return SalaryField(
        raw=section.raw,
        min=min(values) if values else None,
        max=max(values) if values else None,
        currency="CNY" if re.search(r"人民币|元|¥|￥", section.raw) else None,
        period=period,
        source_heading=section.heading,
        source_order=section.source_order,
    )
