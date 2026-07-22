# 影响分析

## 受影响模块与边界

| 模块 | 影响 | 所有权/权限影响 | 备注 |
| --- | --- | --- | --- |
| candidate-profile | 归属从简历推导 | 必须通过简历校验候选人 | 不保留冗余 `candidate_id`。 |
| job-matching | 完整匹配结果才能入库 | 结果查询走归属链 | 禁止持久化不完整评分。 |
| application-management | 创建投递补充归属锚点 | 同事务验证简历、目标和匹配结果 | 初始状态为 `created`。 |
| database-infrastructure | 物理表名与约束收口 | 无 | 必须由 Alembic 执行。 |

## 契约与数据影响

- API：投递创建增加 `goal_id` 与可选 `match_result_id`；画像响应字段统一。
- 数据库与 Alembic：现有 `04-data/` SQL 为审阅产物，实施时绑定唯一 Alembic revision。
- Redis/Celery：无直接变更。

## 风险与缓解

| 风险 | 等级 | 缓解措施 |
| --- | --- | --- |
| 历史空值导致非空约束迁移失败 | high | 迁移先校验并失败，由人工完成历史数据处置。 |
| 关联资源跨候选人混用 | high | Repository 在同一事务校验完整归属链。 |
