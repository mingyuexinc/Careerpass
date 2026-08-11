# 数据库设计

> 本文档描述当前 Alembic 迁移链和 SQLAlchemy Model 已确认的 PostgreSQL 结构，不预定义未来 Slice 的表。

## 1. 迁移链

| Revision | 内容 |
| --- | --- |
| 20260723_0001 | 空基线 |
| 20260725_0002 | users、candidates 认证与身份结构 |
| 20260727_0003 | stored_file_objects、resumes、candidate_profiles、candidate_documents、async_task_runs 及枚举 |
| 20260727_0004 | Dispatcher 与 Worker 的投递/执行租约字段 |

迁移保持单链。新 Schema 变化必须新增 revision，不修改已执行脚本。

## 2. 当前表

| 表 | 主键/归属 | 关键约束 |
| --- | --- | --- |
| users | id | username 唯一；只保存 password_hash |
| candidates | id，user_id → users | user_id 唯一，一对一 |
| stored_file_objects | id | storage_key、content_sha256 唯一 |
| resumes | id，candidate_id → candidates | 引用 ready 文件对象；保存解析状态和失败分类 |
| candidate_profiles | id，resume_id → resumes | resume_id 唯一，一份简历至多一个画像 |
| candidate_documents | id，candidate_id → candidates | 保存资料类型和文件对象引用 |
| async_task_runs | id，resource_id | idempotency_key、celery_task_id 唯一；保存任务、租约和终态 |

## 3. 当前枚举

- stored_file_object_status_enum：writing、ready、deleting
- parse_status_enum：processing、succeeded、failed
- parse_failure_code_enum：unsupported_file、file_unreadable、storage_unavailable、parser_timeout、schema_validation_failed、internal_error
- document_type_enum：certificate、strategy、other
- async_task_type_enum：resume_parse
- async_task_resource_type_enum：resume
- async_task_run_status_enum：queued、running、succeeded、failed

## 4. 一致性边界

- User/Candidate 创建和需要原子提交的业务写入由 Service 协调同一数据库事务。
- 业务表引用 StoredFileObject，但内部 storage_key 不进入业务契约。
- AsyncTaskRun 的投递租约和执行租约分别保护 Dispatcher 与 Worker。
- 当前迁移没有 Job、JobGoal、Match、Application、Conversation、Message 或 ProgressEvent 表。

## 5. 增量规则

具体 Slice 在 Readiness Check 前同步新增表、字段、约束、索引和迁移影响；未进入当前 Slice 的未来结构不得写入本文档。
