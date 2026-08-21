"""Deterministic business rules for S10-03 proactive JobGoal clarification."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.infrastructure.database.models import JobGoal, ParsedJobDescriptionSnapshot
from app.schemas.job_description import ParsedJobDescriptionFields


@dataclass(frozen=True)
class GoalConditionGap:
    """One conservative, binary condition that can be clarified with HR."""

    signature: str
    condition: str
    question: str
    stop_on_yes: bool


@dataclass(frozen=True)
class BinaryAnswer:
    value: bool
    matched: str


_YES = ("是", "对", "属于")
_NO = ("不是", "不对", "不属于")


def find_goal_condition_gap(
    goal: JobGoal | None, snapshot: ParsedJobDescriptionSnapshot | None
) -> GoalConditionGap | None:
    """Return at most one JobGoal condition which the JD cannot confirm.

    The source of truth is the candidate's current JobGoal.  The deliberately
    small vocabulary keeps an ambiguous condition from becoming an external
    decision; new condition types can be added with their own business rule.
    """
    if goal is None or goal.status != "active":
        return None
    filters = _filter_text(goal.filters)
    jd = ""
    fields: ParsedJobDescriptionFields | None = None
    if snapshot is not None:
        fields = ParsedJobDescriptionFields.model_validate(snapshot.fields)
        jd = " ".join(
            str(value)
            for value in fields.model_dump(mode="python").values()
            if value not in (None, "", [], {})
        )
    jd_normalized = jd.casefold()
    for clause in _clauses(filters):
        if "外包" in clause or "外派" in clause:
            # Only job nature/employment type can confirm this condition.
            # A mention in responsibilities, requirements or summary is not
            # evidence that the position itself is an outsourcing position.
            nature = _text_field_value(fields.job_nature if fields else None)
            employment = _text_field_value(fields.employment_type if fields else None)
            if any(marker in f"{nature} {employment}".casefold() for marker in ("外包", "外派")):
                continue
            condition = "该岗位是否属于外包岗位"
            return _gap(condition, "请确认一下，这个岗位是否属于外包岗位？", _negative_preference(clause))
        if any(marker in clause for marker in ("薪资", "工资", "月薪", "不低于", "至少", ">=")):
            # Salary is already a matching-stage hard filter in the current
            # slice and must not be asked again.
            continue
        if _is_matching_stage_location_filter(clause):
            # Excluded locations are also consumed by the matching stage.
            # They must not become a second HR question after an Application
            # has already been created.
            continue
        condition = _condition_text(clause)
        if condition and condition.casefold() not in jd_normalized:
            return _gap(
                condition,
                f"请确认一下，这个岗位是否{condition}？",
                _negative_preference(clause),
            )
    return None


def parse_binary_answer(content: str) -> BinaryAnswer | None:
    """Extract one unambiguous binary expression and ignore extra explanation."""
    text = re.sub(r"\s+", "", content)
    yes: list[str] = []
    for token in _YES:
        if any(match.start() == 0 or text[match.start() - 1] != "不" for match in re.finditer(token, text)):
            yes.append(token)
    no = [token for token in _NO if token in text]
    # Prefer the longer negative forms.  Mixed or otherwise unclear answers
    # stay pending, exactly as required by the business rule.
    if no and not yes:
        return BinaryAnswer(value=False, matched=max(no, key=len))
    if yes and not no:
        return BinaryAnswer(value=True, matched=max(yes, key=len))
    return None


def _gap(condition: str, question: str, stop_on_yes: bool) -> GoalConditionGap:
    signature = hashlib.sha256(condition.encode("utf-8")).hexdigest()[:24]
    return GoalConditionGap(
        signature=signature,
        condition=condition,
        question=question,
        stop_on_yes=stop_on_yes,
    )


def _filter_text(value: object) -> str:
    if isinstance(value, str):
        return value
    return str(value or "")


def _clauses(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[\n;,，；。]+", value) if item.strip()]


def _negative_preference(clause: str) -> bool:
    return any(marker in clause for marker in ("不考虑", "不接受", "拒绝", "不要", "排除"))


def _condition_text(clause: str) -> str:
    value = clause
    for marker in ("不考虑", "不接受", "拒绝", "不要", "排除", "优先", "希望", "倾向于"):
        value = value.replace(marker, "")
    value = value.strip(" ：:的岗位职位")
    return value if len(value) >= 2 else ""


def _text_field_value(value: object | None) -> str:
    if value is None:
        return ""
    raw = getattr(value, "raw", None)
    normalized = getattr(value, "normalized", None)
    return str(normalized or raw or "")


def _is_matching_stage_location_filter(clause: str) -> bool:
    has_exclusion = any(marker in clause for marker in ("不考虑", "不接受", "排除", "不要"))
    has_location_wording = any(
        marker in clause for marker in ("工作地点", "地区", "城市", "的工作岗位", "的工作职位")
    )
    return has_exclusion and has_location_wording
