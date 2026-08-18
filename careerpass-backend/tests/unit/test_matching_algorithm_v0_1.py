from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.parsers.job_description import parse_job_description
from app.services.matching_algorithm_v0_1 import (
    CandidateMatchingSummary,
    JobGoalMatchingSummary,
    JobMatchingSummary,
    evaluate,
)


def _job(*, title: str = "AI 应用开发工程师", location: str = "深圳", salary: str = "25k-40k") -> JobMatchingSummary:
    content = f"""# {title}

## 工作地点
{location}

## 薪资
{salary}

## 岗位职责
- 使用 Python、FastAPI 开发 AI Agent 应用

## 任职要求
- 熟悉 Python、RAG、Agent 和 Docker
""".encode()
    fields, _ = parse_job_description(content)
    return JobMatchingSummary(job_id=uuid4(), created_at=datetime.now(UTC), fields=fields)


def _candidate(years: str = "3年") -> CandidateMatchingSummary:
    return CandidateMatchingSummary(
        target_job_titles=["AI 应用开发工程师"],
        skills=["Python", "FastAPI", "RAG", "Agent", "Docker"],
        experience_titles=["AI 应用开发工程师"],
        experience_summaries=["负责 AI Agent 应用开发"],
        years_of_experience=years,
    )


def test_hard_location_and_salary_filters_are_exclusion_results() -> None:
    goal = JobGoalMatchingSummary(title="AI 应用开发", filters="不考虑北京，薪资不低于20K")
    assert evaluate(job=_job(location="北京", salary="25k-40k"), candidate=_candidate(), goal=goal).status == "filtered_out"
    assert evaluate(job=_job(location="深圳", salary="18k-30k"), candidate=_candidate(), goal=goal).status == "filtered_out"


def test_location_filter_normalizes_workplace_suffixes_before_scoring() -> None:
    candidate = _candidate()
    for filters in (
        "不考虑北京",
        "不考虑北京作为工作地点",
        "不考虑北京的工作地点",
        "不考虑北京的工作岗位",
        "不考虑北京地区",
    ):
        result = evaluate(
            job=_job(location="北京"),
            candidate=candidate,
            goal=JobGoalMatchingSummary(title="AI 应用开发", filters=filters),
        )
        assert result.status == "filtered_out"
        assert result.reason_code == "excluded_location"
        assert result.role_score is None
        assert result.level_score is None
        assert result.skill_score is None
        assert result.total_score is None


def test_soft_preference_and_unknown_text_do_not_filter() -> None:
    job = _job()
    candidate = _candidate()
    assert evaluate(
        job=job, candidate=candidate,
        goal=JobGoalMatchingSummary(title="AI 应用开发", filters="优先北京"),
    ).status == "matched"
    assert evaluate(
        job=job, candidate=candidate,
        goal=JobGoalMatchingSummary(title="AI 应用开发", filters="希望团队氛围好"),
    ).status == "matched"


def test_non_ai_backend_job_is_filtered_by_supported_job_family() -> None:
    result = evaluate(
        job=_job(title="后端开发工程师"), candidate=_candidate(),
        goal=JobGoalMatchingSummary(title="AI 应用开发"),
    )
    assert result.status == "filtered_out"
    assert result.reason_code == "unsupported_job_family"


def test_scores_are_independent_but_compensate_in_weighted_total() -> None:
    result = evaluate(
        job=_job(), candidate=_candidate(),
        goal=JobGoalMatchingSummary(title="AI 应用开发"),
    )
    assert result.role_score == 100
    assert result.level_score == 100
    assert result.skill_score == 100
    assert result.total_score == 100


def test_two_level_difference_gives_zero_level_dimension() -> None:
    result = evaluate(
        job=_job(title="高级 AI 应用开发工程师"), candidate=_candidate(years="1年"),
        goal=JobGoalMatchingSummary(title="AI 应用开发"),
    )
    assert result.level_score == 0
