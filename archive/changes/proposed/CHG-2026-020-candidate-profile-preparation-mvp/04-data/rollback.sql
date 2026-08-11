-- 审阅用回滚摘要；运行时通过 Alembic downgrade 20260725_0002 执行。
--
-- 反向依赖顺序：async_task_runs → candidate_documents → candidate_profiles
-- → resumes → stored_file_objects → 本次新增 PostgreSQL 枚举类型。
-- 不删除 users、candidates 或 set_updated_at()，因为它们属于认证基础变更。
-- Subtask 4 review summary. Apply through Alembic downgrade 20260727_0003 only.
DROP INDEX IF EXISTS idx_async_task_run_dispatch_lease;
ALTER TABLE async_task_runs DROP COLUMN IF EXISTS dispatched_at;
ALTER TABLE async_task_runs DROP COLUMN IF EXISTS dispatch_lease_expires_at;
ALTER TABLE async_task_runs DROP COLUMN IF EXISTS dispatch_token;
