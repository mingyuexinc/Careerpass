"""Deterministic S-08岗位匹配算法 v0.1.

The algorithm consumes validated semantic summaries only. It has no database,
file-system, LLM, or HTTP dependency and can therefore be tested independently
from the orchestration service.
"""

from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job_description import ParsedJobDescriptionFields

ALGORITHM_VERSION = "v0.1"
ROLE_WEIGHT = 0.35
LEVEL_WEIGHT = 0.25
SKILL_WEIGHT = 0.40
MATCH_THRESHOLD = 60.0
MatchStatus = Literal["filtered_out", "not_matched", "matched"]
Level = Literal["low", "mid", "high"]


class CandidateMatchingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_job_titles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_titles: list[str] = Field(default_factory=list)
    experience_summaries: list[str] = Field(default_factory=list)
    project_technologies: list[str] = Field(default_factory=list)
    project_summaries: list[str] = Field(default_factory=list)
    years_of_experience: str = "unknown"


class JobMatchingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: UUID
    created_at: datetime
    fields: ParsedJobDescriptionFields


class JobGoalMatchingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    filters: str = ""


class MatchingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: MatchStatus
    role_score: float | None = None
    level_score: float | None = None
    skill_score: float | None = None
    total_score: float | None = None
    recommendation_reason: str
    reason_code: str
    filter_reason: str | None = None
    input_snapshot: dict[str, object]


_AI_TERMS = (
    "ai", "人工智能", "大模型", "大语言模型", "llm", "agent", "智能体",
    "rag", "aigc", "机器学习", "深度学习", "nlp", "mcp",
)
_DEVELOPMENT_TERMS = (
    "开发", "工程", "软件", "应用", "后端", "前端", "全栈", "架构",
    "developer", "engineer", "software", "backend", "frontend", "fullstack",
)
_HIGH_TERMS = ("高级", "资深", "专家", "负责人", "lead", "principal", "staff", "总监")
_LOW_TERMS = ("初级", "助理", "实习", "junior", "entry")
_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python",), "javascript": ("javascript", "js"),
    "typescript": ("typescript", "ts"), "java": ("java",),
    "go": ("golang", "go语言"), "c++": ("c++",), "react": ("react",),
    "vue": ("vue",), "node.js": ("node.js", "nodejs", "node"),
    "fastapi": ("fastapi",), "langchain": ("langchain",),
    "langgraph": ("langgraph",), "llm": ("llm", "大模型", "大语言模型"),
    "agent": ("agent", "智能体"), "rag": ("rag", "检索增强生成"),
    "function_calling": ("function calling", "函数调用", "tool calling", "工具调用"),
    "prompt": ("prompt", "提示词"), "memory": ("memory", "记忆管理"),
    "context": ("context", "上下文管理"), "mysql": ("mysql",),
    "postgresql": ("postgresql", "postgres"), "redis": ("redis",),
    "docker": ("docker", "容器化"), "kubernetes": ("kubernetes", "k8s"),
    "mcp": ("mcp",), "api": ("api", "接口服务"),
    "async_tasks": ("异步任务", "celery"),
}


def evaluate(*, job: JobMatchingSummary, candidate: CandidateMatchingSummary,
             goal: JobGoalMatchingSummary) -> MatchingResult:
    semantic_snapshot = _input_snapshot(job=job, candidate=candidate, goal=goal)
    filters = _parse_filters(goal.filters)
    filter_reason = _hard_filter_reason(job=job, filters=filters)
    if filter_reason is not None:
        reason_code, label = filter_reason
        return MatchingResult(
            status="filtered_out",
            recommendation_reason=f"岗位因{label}被排除，未进入匹配评分。",
            reason_code=reason_code,
            filter_reason=label,
            input_snapshot=semantic_snapshot,
        )

    title = job.fields.title.normalized or job.fields.title.raw
    role_score, role_result = _role_score(title, candidate)
    job_level = _infer_job_level(job)
    candidate_level = _infer_candidate_level(candidate)
    level_score, level_result = _level_score(job_level, candidate_level)
    skill_score, skill_result = _skill_score(job.fields, candidate)
    total = round(role_score * ROLE_WEIGHT + level_score * LEVEL_WEIGHT + skill_score * SKILL_WEIGHT, 2)
    status: MatchStatus = "matched" if total >= MATCH_THRESHOLD else "not_matched"
    if status == "matched":
        reason = f"岗位画像{role_result}；能力层级{level_result}；技能匹配{skill_result}；综合匹配得分{round(total):.0f}。"
        reason_code = "matched"
    else:
        reason = f"岗位画像{role_result}；能力层级{level_result}；技能匹配{skill_result}；综合得分{round(total):.0f}未达到匹配阈值。"
        reason_code = "below_threshold"
    return MatchingResult(
        status=status, role_score=round(role_score, 2), level_score=round(level_score, 2),
        skill_score=round(skill_score, 2), total_score=total,
        recommendation_reason=reason, reason_code=reason_code,
        input_snapshot=semantic_snapshot,
    )


def stable_sort_key(job: JobMatchingSummary) -> tuple[datetime, str]:
    return job.created_at, str(job.job_id)


def _hard_filter_reason(*, job: JobMatchingSummary, filters: dict[str, object]) -> tuple[str, str] | None:
    location = _normalize(job.fields.location.normalized or job.fields.location.raw)
    excluded_locations = filters["excluded_locations"]
    if any(_normalize(value) in location for value in excluded_locations):
        return "excluded_location", "用户排除的工作地点"
    minimum_salary = filters["minimum_salary_k"]
    if minimum_salary is not None:
        salary = job.fields.salary_range
        job_min = _salary_k(salary.min if salary.min is not None else salary.max)
        if job_min is not None and job_min < minimum_salary:
            return "salary_below_minimum", "薪资低于用户设定的最低要求"
    title = job.fields.title.normalized or job.fields.title.raw
    if not _is_ai_software_job(title):
        return "unsupported_job_family", "当前版本不支持的岗位族"
    return None


def _parse_filters(value: str) -> dict[str, object]:
    text = value.strip()
    excluded: list[str] = []
    for match in re.finditer(r"(?:不考虑|不接受|排除|不要)\s*([^，,。；;\s]+)", text):
        candidate = _normalize_excluded_location(match.group(1))
        if candidate and not _contains_soft_preference(text, match.start(), match.end()):
            excluded.append(candidate)
    minimum_salary_k: float | None = None
    salary_match = re.search(
        r"(?:薪资|工资|月薪)?\s*(?:不低于|至少|最低|大于等于|>=)\s*"
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[kK万]?)", text, flags=re.IGNORECASE,
    )
    if salary_match and not _contains_soft_preference(text, salary_match.start(), salary_match.end()):
        number = float(salary_match.group("value"))
        minimum_salary_k = number * 10 if salary_match.group("unit") == "万" else number
    return {"excluded_locations": tuple(excluded), "minimum_salary_k": minimum_salary_k}


def _normalize_excluded_location(value: str) -> str:
    """Reduce natural-language location descriptions to comparable values."""
    candidate = value.strip()
    candidate = re.sub(r"(?:作为|的)?(?:工作)?(?:地点|岗位|职位)$", "", candidate)
    candidate = re.sub(r"(?:地区|城市)$", "", candidate)
    return candidate.strip()


def _contains_soft_preference(text: str, start: int, end: int) -> bool:
    return "优先" in text[max(0, start - 4): min(len(text), end + 4)]


def _is_ai_software_job(title: str) -> bool:
    normalized = _normalize(title)
    return any(term in normalized for term in _AI_TERMS) and any(
        term in normalized for term in _DEVELOPMENT_TERMS
    )


def _role_score(title: str, candidate: CandidateMatchingSummary) -> tuple[float, str]:
    job_title = _normalize(title)
    candidate_text = _normalize(" ".join(_candidate_role_text(candidate)))
    if not candidate_text:
        return 0.0, "暂无明确候选人岗位方向证据"
    if any(title_similarity(title, candidate_title) >= 0.78 for candidate_title in candidate.target_job_titles):
        return 100.0, "高度匹配"
    if any(term in candidate_text for term in _AI_TERMS):
        if any(term in job_title and term in candidate_text for term in ("agent", "智能体", "rag", "llm", "大模型")):
            return 100.0, "高度匹配"
        return 80.0, "同属 AI 软件开发方向"
    if any(term in candidate_text for term in ("开发", "软件", "后端", "前端", "工程")):
        return 40.0, "具备通用软件开发方向但缺少 AI 证据"
    return 0.0, "岗位方向不一致"


def _infer_job_level(job: JobMatchingSummary) -> Level:
    title = _normalize(job.fields.title.normalized or job.fields.title.raw)
    text = _normalize(" ".join(_section_text(job.fields)))
    if any(term in title or term in text for term in _HIGH_TERMS):
        return "high"
    if any(term in title or term in text for term in _LOW_TERMS):
        return "low"
    return _level_from_years(_extract_years(text))


def _infer_candidate_level(candidate: CandidateMatchingSummary) -> Level:
    text = _normalize(" ".join(_candidate_role_text(candidate)))
    if any(term in text for term in _HIGH_TERMS):
        return "high"
    if any(term in text for term in _LOW_TERMS):
        return "low"
    return _level_from_years(_extract_years(candidate.years_of_experience))


def _level_from_years(years: float | None) -> Level:
    if years is None:
        return "mid"
    if years <= 2:
        return "low"
    if years <= 5:
        return "mid"
    return "high"


def _extract_years(value: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:年|years?)", value.casefold())
    if match:
        return float(match.group(1))
    months = re.search(r"(\d+(?:\.\d+)?)\s*个月", value)
    return float(months.group(1)) / 12 if months else None


def _salary_k(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 1000 if value > 1000 else value


def _level_score(job_level: Level, candidate_level: Level) -> tuple[float, str]:
    distance = abs(("low", "mid", "high").index(job_level) - ("low", "mid", "high").index(candidate_level))
    if distance == 0:
        return 100.0, "同级"
    if distance == 1:
        return 60.0, "相差一级"
    return 0.0, "相差两级"


def _skill_score(fields: ParsedJobDescriptionFields, candidate: CandidateMatchingSummary) -> tuple[float, str]:
    required = _extract_skills(_section_text(fields))
    available = _extract_skills([
        *candidate.skills, *candidate.experience_titles, *candidate.experience_summaries,
        *candidate.project_technologies, *candidate.project_summaries,
    ])
    if not required:
        return 0.0, "未提取到明确技能项"
    matched = required & available
    score = len(matched) / len(required) * 100 if available else 0.0
    return score, f"覆盖{len(matched)}/{len(required)}项技能"


def _extract_skills(values: list[str]) -> set[str]:
    text = _normalize(" ".join(values))
    result: set[str] = set()
    for canonical, aliases in _SKILL_ALIASES.items():
        if any(_normalize(alias) in text for alias in aliases):
            result.add(canonical)
    return result


def _candidate_role_text(candidate: CandidateMatchingSummary) -> list[str]:
    return [*candidate.target_job_titles, *candidate.experience_titles, *candidate.experience_summaries]


def _section_text(fields: ParsedJobDescriptionFields) -> list[str]:
    return [*[item.normalized or item.raw for item in fields.responsibilities.items],
            *[item.normalized or item.raw for item in fields.requirements.items]]


def _input_snapshot(*, job: JobMatchingSummary, candidate: CandidateMatchingSummary,
                    goal: JobGoalMatchingSummary) -> dict[str, object]:
    fields = job.fields
    salary = fields.salary_range
    return {"algorithm_input": {
        "job": {
            "title": fields.title.normalized or fields.title.raw,
            "location": fields.location.normalized or fields.location.raw,
            "salary": {"min": salary.min, "max": salary.max, "currency": salary.currency},
            "responsibilities": [item.normalized or item.raw for item in fields.responsibilities.items],
            "requirements": [item.normalized or item.raw for item in fields.requirements.items],
        },
        "candidate": candidate.model_dump(mode="json"),
        "goal": {"title": goal.title, "recognized_filters": _parse_filters(goal.filters)},
    }}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value.casefold().replace("ＡＩ", "ai"))


def title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()
