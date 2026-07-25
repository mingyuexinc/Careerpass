"""Celery configuration and side-effect-free runtime probes."""

from app.infrastructure.tasks.celery_app import create_celery_app

__all__ = ["create_celery_app"]
