"""FastAPI application factory for CareerPass."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import request_context_middleware
from app.infrastructure.cache import create_redis_client
from app.infrastructure.database import create_database
from app.infrastructure.runtime import check_celery_configuration, check_database, check_redis
from app.infrastructure.tasks import create_celery_app
from app.services.runtime_health_service import RuntimeHealthService


def create_app() -> FastAPI:
    """Create a configured application without initializing external services."""
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = create_database(
            str(settings.database_url),
            pool_size=settings.database_pool_size,
        )
        redis_client = create_redis_client(str(settings.redis_url))
        celery_app = create_celery_app(
            str(settings.redis_url),
            task_time_limit_seconds=settings.celery_task_time_limit_seconds,
        )
        app.state.database = database
        app.state.redis_client = redis_client
        app.state.celery_app = celery_app
        app.state.runtime_health_service = RuntimeHealthService(
            database_probe=lambda: check_database(
                database.engine,
                settings.readiness_timeout_seconds,
            ),
            redis_probe=lambda: check_redis(
                redis_client.client,
                settings.readiness_timeout_seconds,
            ),
            celery_probe=lambda: check_celery_configuration(celery_app),
        )
        try:
            yield
        finally:
            await redis_client.close()
            await database.close()

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.middleware("http")(request_context_middleware)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
