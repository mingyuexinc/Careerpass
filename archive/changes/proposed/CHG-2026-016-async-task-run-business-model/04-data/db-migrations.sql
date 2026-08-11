-- 审阅用正向迁移脚本；运行时仅可通过工程内 Alembic revision 执行。

CREATE TYPE async_task_type_enum AS ENUM (
    'resume_parse',
    'job_description_parse',
    'job_matching'
);

CREATE TYPE async_task_resource_type_enum AS ENUM (
    'resume',
    'job_description',
    'match_run'
);

CREATE TYPE async_task_run_status_enum AS ENUM (
    'queued',
    'running',
    'succeeded',
    'failed'
);

CREATE TYPE parse_failure_code_enum AS ENUM (
    'unsupported_file',
    'file_unreadable',
    'storage_unavailable',
    'parser_timeout',
    'schema_validation_failed',
    'internal_error'
);

CREATE TABLE async_task_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type async_task_type_enum NOT NULL,
    resource_type async_task_resource_type_enum NOT NULL,
    resource_id UUID NOT NULL,
    celery_task_id VARCHAR(255) NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    status async_task_run_status_enum NOT NULL DEFAULT 'queued',
    task_version VARCHAR(128) NOT NULL,
    failure_code parse_failure_code_enum NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ NULL,
    CONSTRAINT ck_async_task_run_finished_at
        CHECK (
            (status IN ('queued', 'running') AND finished_at IS NULL)
            OR (status IN ('succeeded', 'failed') AND finished_at IS NOT NULL)
        ),
    CONSTRAINT ck_async_task_run_failure_code
        CHECK (
            (status = 'failed' AND failure_code IS NOT NULL)
            OR (status <> 'failed' AND failure_code IS NULL)
        ),
    CONSTRAINT ck_async_task_run_celery_id_before_execution
        CHECK (
            status = 'queued' OR celery_task_id IS NOT NULL
        )
);

CREATE UNIQUE INDEX uq_async_task_run_celery_task
    ON async_task_runs (celery_task_id)
    WHERE celery_task_id IS NOT NULL;

CREATE UNIQUE INDEX uq_async_task_run_idempotency
    ON async_task_runs (resource_type, resource_id, task_type, task_version, idempotency_key);

CREATE INDEX idx_async_task_run_resource
    ON async_task_runs (resource_type, resource_id);

CREATE INDEX idx_async_task_run_status
    ON async_task_runs (status);

CREATE INDEX idx_async_task_run_pending_dispatch
    ON async_task_runs (created_at)
    WHERE status = 'queued' AND celery_task_id IS NULL;
