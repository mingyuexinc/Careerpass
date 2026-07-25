"""Celery application factory and a constrained runtime probe task."""

from celery import Celery
from pydantic import BaseModel, Field


class RuntimeProbePayload(BaseModel):
    """Validated input for the non-business probe task."""

    idempotency_key: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


def create_celery_app(
    redis_url: str,
    *,
    task_time_limit_seconds: int,
    always_eager: bool = False,
) -> Celery:
    """Create a Celery app with explicit serialization, timeout and state settings."""
    celery_app = Celery("careerpass")
    celery_app.conf.update(
        broker_url=redis_url,
        result_backend=redis_url,
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
        task_track_started=True,
        task_time_limit=task_time_limit_seconds,
        task_acks_late=True,
        task_always_eager=always_eager,
        task_store_eager_result=False,
    )

    @celery_app.task(
        name="careerpass.runtime_probe",
        bind=True,
        autoretry_for=(ConnectionError, TimeoutError),
        retry_backoff=True,
        retry_jitter=True,
        retry_kwargs={"max_retries": 3},
    )
    def runtime_probe(_: object, payload: dict[str, object]) -> dict[str, str]:
        """Validate routing/state behavior without external or business side effects."""
        validated_payload = RuntimeProbePayload.model_validate(payload)
        return {"status": "succeeded", "idempotency_key": validated_payload.idempotency_key}

    return celery_app
