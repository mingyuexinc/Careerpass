"""Unit coverage for the deterministic S-03 Markdown parser."""

from pathlib import Path

import pytest

from app.parsers.job_description import JobDescriptionParseError, parse_job_description

FIXTURE = (
    Path(__file__).parents[3]
    / "fixtures"
    / "job_descriptions"
    / "001-天创机器人-Agent开发工程师.md"
)


def test_parser_preserves_core_fields_extra_fields_and_source_order() -> None:
    fields, raw_sections = parse_job_description(FIXTURE.read_bytes())

    assert fields.title.raw == "001-天创机器人-Agent开发工程师"
    assert fields.title.source_order == 0
    assert fields.company_name is not None
    assert fields.company_name.normalized == "天创机器人"
    assert fields.location.normalized == "南京"
    assert fields.salary_range.min == 18_000
    assert fields.salary_range.max == 35_000
    assert fields.salary_range.period == "month"
    assert len(fields.responsibilities.items) == 4
    assert len(fields.requirements.items) == 4
    extra_fields, _ = parse_job_description(
        """# 数据工程师

## 工作地点
北京

## 薪资
20k-30k/月

## 岗位职责
负责开发

## 任职要求
熟悉 Python

## 工作模式
远程
""".encode()
    )
    assert extra_fields.additional_fields["工作模式"].raw == "远程"
    assert raw_sections[0]["raw"] == "001-天创机器人-Agent开发工程师"


def test_parser_rejects_missing_core_fields_without_fabricating_values() -> None:
    with pytest.raises(JobDescriptionParseError) as error:
        parse_job_description("# 工程师\n\n## 工作地点\n上海\n".encode())

    assert error.value.missing_core_fields == ["salary_range", "responsibilities", "requirements"]


def test_parser_preserves_non_bullet_section_text() -> None:
    fields, _ = parse_job_description(
        """# 数据工程师

## 工作地点
北京

## 薪资
15k/月

## 岗位职责
负责数据平台建设。

## 任职要求
熟悉 Python。
""".encode()
    )

    assert fields.responsibilities.raw == "负责数据平台建设。"
    assert fields.responsibilities.items == []
    assert fields.requirements.raw == "熟悉 Python。"
