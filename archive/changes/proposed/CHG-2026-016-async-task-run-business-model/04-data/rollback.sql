-- 仅回滚本次新增对象；按依赖反向顺序执行。

DROP TABLE IF EXISTS async_task_runs;
DROP TYPE IF EXISTS parse_failure_code_enum;
DROP TYPE IF EXISTS async_task_run_status_enum;
DROP TYPE IF EXISTS async_task_resource_type_enum;
DROP TYPE IF EXISTS async_task_type_enum;
