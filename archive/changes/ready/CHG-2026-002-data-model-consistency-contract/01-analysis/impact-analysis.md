# 影响分析

## 受影响模块与边界

| 模块 | 影响 | 所有权/权限影响 | 备注 |
| --- | --- | --- | --- |
| document-processing | 解析状态统一 | 无新增权限 | 异步状态必须可追踪。 |
| application-management | 应用字段名统一 | 既有候选人归属校验 | 需同步 API Schema。 |
| communication | 消息角色、附件和会话时间统一 | 会话归属链不变 | 最后消息时间由触发器维护。 |
| database-infrastructure | 索引与触发器调整 | 无 | 通过 Alembic 执行。 |

## 契约与数据影响

- API：统一 `match_result_id`、`status`、`role`、`file_url`。
- 数据库与 Alembic：索引重命名、解析状态默认值及会话触发器均需单独审阅的迁移。
- Redis/Celery：解析任务必须从 `processing` 合法迁移。

## 风险与缓解

| 风险 | 等级 | 缓解措施 |
| --- | --- | --- |
| 迁移后字段名或状态与调用方不一致 | high | 先更新契约，再以集成测试覆盖读写路径。 |
