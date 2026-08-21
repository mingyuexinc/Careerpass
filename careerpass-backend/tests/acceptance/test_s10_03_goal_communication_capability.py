"""Deterministic S10-03 capability acceptance checks."""

from types import SimpleNamespace

import pytest

from app.services.s10_03_goal_communication import find_goal_condition_gap, parse_binary_answer

pytestmark = pytest.mark.capability_acceptance


def _goal(filters: str = "不考虑外包岗位") -> SimpleNamespace:
    return SimpleNamespace(status="active", filters=filters)


def test_unconfirmed_goal_condition_creates_one_query() -> None:
    gap = find_goal_condition_gap(_goal(), None)
    assert gap is not None
    assert gap.question == "请确认一下，这个岗位是否属于外包岗位？"
    assert gap.stop_on_yes is True


def test_leading_free_text_before_outsourcing_condition_is_supported() -> None:
    gap = find_goal_condition_gap(_goal("....不考虑外包岗位"), None)
    assert gap is not None
    assert gap.signature


def test_condition_is_not_limited_to_outsourcing() -> None:
    gap = find_goal_condition_gap(_goal("不接受倒班"), None)
    assert gap is not None
    assert "倒班" in gap.question


def test_matching_stage_location_filter_is_not_asked_again() -> None:
    gap = find_goal_condition_gap(_goal("不考虑北京的工作岗位，不考虑外包岗位"), None)
    assert gap is not None
    assert "外包" in gap.question


def test_jd_confirmed_condition_has_no_query() -> None:
    snapshot = SimpleNamespace(
        fields={
            "title": {"raw": "工程师", "source_heading": "职位", "source_order": 0},
            "location": {"raw": "上海", "source_heading": "地点", "source_order": 1},
            "salary_range": {"raw": "面议", "source_heading": "薪资", "source_order": 2},
            "responsibilities": {"raw": "开发", "items": [], "source_heading": "职责", "source_order": 3},
            "requirements": {"raw": "经验", "items": [], "source_heading": "要求", "source_order": 4},
            "job_nature": {"raw": "外包", "source_heading": "性质", "source_order": 5},
        }
    )
    assert find_goal_condition_gap(_goal(), snapshot) is None


def test_jd_summary_mention_does_not_confirm_job_nature() -> None:
    snapshot = SimpleNamespace(
        fields={
            "title": {"raw": "工程师", "source_heading": "职位", "source_order": 0},
            "location": {"raw": "上海", "source_heading": "地点", "source_order": 1},
            "salary_range": {"raw": "面议", "source_heading": "薪资", "source_order": 2},
            "responsibilities": {"raw": "开发", "items": [], "source_heading": "职责", "source_order": 3},
            "requirements": {"raw": "经验", "items": [], "source_heading": "要求", "source_order": 4},
            "summary": {"raw": "不涉及外包说明", "source_heading": "摘要", "source_order": 5},
        }
    )
    assert find_goal_condition_gap(_goal(), snapshot) is not None


@pytest.mark.parametrize(
    ("content", "value"),
    [("是", True), ("不是", False), ("对，岗位确实如此", True), ("不属于外包岗位，补充说明如下", False)],
)
def test_binary_answer_accepts_common_forms_and_extra_text(content: str, value: bool) -> None:
    answer = parse_binary_answer(content)
    assert answer is not None and answer.value is value


@pytest.mark.parametrize("content", ["不确定", "是，也不是", "这个问题我再确认一下"])
def test_binary_answer_fails_closed(content: str) -> None:
    assert parse_binary_answer(content) is None
