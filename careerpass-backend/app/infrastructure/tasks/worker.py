"""Celery worker entry point for deployed runtime probe tasks."""

from app.core.config import get_settings
from app.infrastructure.tasks.celery_app import create_celery_app

settings = get_settings()
celery_app = create_celery_app(
    str(settings.redis_url),
    task_time_limit_seconds=settings.celery_task_time_limit_seconds,
)
