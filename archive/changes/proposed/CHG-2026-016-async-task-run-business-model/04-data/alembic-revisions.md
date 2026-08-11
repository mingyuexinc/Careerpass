# Alembic 修订说明

当前变更包只提供评审用 SQL，不包含工程运行时 Alembic revision。

在候选人资料准备的实现变更中，必须新增一条 Alembic revision，按当前数据模型创建候选人画像的 `target_job_titles VARCHAR(128)[] NOT NULL`、非空数组检查约束与 `resume_id` 唯一约束，并按 `db-migrations.sql` 创建四个枚举、`async_task_runs` 表、全量幂等唯一约束和待投递部分索引；候选人附加资料不属于 `async_task_runs` 的资源类型。降级时按 `rollback.sql` 的反向顺序仅移除本次新增对象。运行时迁移的唯一入口是 `careerpass-backend/alembic/versions/` 下的 revision，禁止直接执行本目录 SQL。
