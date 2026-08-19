from app.repositories.matching_repository import _experience_highlights


def test_matching_repository_flattens_work_and_project_highlights() -> None:
    values = [
        {"highlights": ["RAG", "FastAPI"]},
        {"highlights": [], "summary": "ignored here"},
        {"highlights": ["PostgreSQL"]},
    ]

    assert _experience_highlights(values) == ["RAG", "FastAPI", "PostgreSQL"]
