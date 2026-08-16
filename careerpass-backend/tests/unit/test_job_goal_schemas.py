import pytest
from pydantic import ValidationError

from app.schemas.job_goal import JobGoalInput


def test_job_goal_input_normalizes_text_and_accepts_empty_filters() -> None:
    value = JobGoalInput(offer_target=3, title="  后端开发  ", filters="  优先 AI  ")

    assert value.offer_target == 3
    assert value.title == "后端开发"
    assert value.filters == "优先 AI"


@pytest.mark.parametrize("offer_target", [0, -1, 11, 1.5, "3"])
def test_job_goal_input_rejects_invalid_offer_target(offer_target: object) -> None:
    with pytest.raises(ValidationError):
        JobGoalInput(offer_target=offer_target, title="后端开发", filters="")


def test_job_goal_input_requires_non_blank_title_and_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        JobGoalInput(offer_target=1, title="  ", filters="")
    with pytest.raises(ValidationError):
        JobGoalInput(offer_target=1, title="后端开发", filters="", resume_id="resume")
