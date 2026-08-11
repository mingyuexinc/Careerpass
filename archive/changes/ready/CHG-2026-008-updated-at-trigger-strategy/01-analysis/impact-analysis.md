# 影响分析

## 受影响模块与边界

| 模块 | 影响 | 所有权/权限影响 | 备注 |
| --- | --- | --- | --- |
| user-management | `users.updated_at` 由数据库维护 | 无 | 不接受外部时间输入。 |
| candidate-management | `candidates.updated_at` 由数据库维护 | 无 | 创建时间保持不变。 |
| repository | 不再手动设置或信任更新时间 | 不改变资源归属校验 | 所有更新路径受触发器覆盖。 |
| database-infrastructure | 提供共享函数与表级触发器 | 无 | 经 Alembic 迁移。 |

## 契约与数据影响

- API：无。
- 数据库与 Alembic：现有 `04-data/` SQL 为审阅产物；实施时生成唯一 revision。
- Redis/Celery：无。

## 风险与缓解

| 风险 | 等级 | 缓解措施 |
| --- | --- | --- |
| 触发器依赖被回滚错误删除 | high | 先解绑表级触发器，再确认无依赖后删除函数。 |
