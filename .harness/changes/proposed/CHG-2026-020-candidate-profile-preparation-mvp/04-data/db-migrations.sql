-- 审阅用摘要；运行时唯一迁移入口为
-- careerpass-backend/alembic/versions/20260727_0003_candidate_preparation.py。
--
-- 新增：stored_file_objects、resumes、candidate_profiles、candidate_documents、async_task_runs。
-- 关键保护：内容摘要/对象键唯一、候选人归属外键、上传幂等部分唯一索引、
-- 画像来源简历唯一、文件大小与画像年限检查、任务终态/失败原因检查、
-- pending-dispatch 部分索引，以及 stored_file_objects 的 updated_at 触发器。
-- Subtask 4 review summary. Apply through Alembic revision 20260727_0004 only.
ALTER TABLE async_task_runs ADD COLUMN IF NOT EXISTS dispatch_token UUID NULL;
ALTER TABLE async_task_runs ADD COLUMN IF NOT EXISTS dispatch_lease_expires_at TIMESTAMPTZ NULL;
ALTER TABLE async_task_runs ADD COLUMN IF NOT EXISTS dispatched_at TIMESTAMPTZ NULL;
CREATE INDEX IF NOT EXISTS idx_async_task_run_dispatch_lease
    ON async_task_runs (status, dispatched_at, dispatch_lease_expires_at);
