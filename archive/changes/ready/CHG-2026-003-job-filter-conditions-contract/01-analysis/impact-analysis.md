# 影响分析

## 受影响模块与边界

| 模块 | 影响 | 所有权/权限影响 | 备注 |
| --- | --- | --- | --- |
| job-goal-management | 持久化并校验 `filter_conditions` | 仅允许访问所属求职目标 | 空对象合法。 |
| job-matching | 将已提供条件转为过滤逻辑 | 使用已校验的目标 | 未提供条件不参与过滤。 |
| communication | 读取求职目标过滤偏好 | 不改变会话归属 | 不直接接受模型未校验输入。 |

## 契约与数据影响

- API：创建求职目标请求必须包含 `filter_conditions`。
- 数据库与 Alembic：复用既有 JSONB 字段，无 Schema 迁移。
- Redis/Celery：无。

## 风险与缓解

| 风险 | 等级 | 缓解措施 |
| --- | --- | --- |
| 空值和空对象语义混淆 | medium | Pydantic Schema 明确对象必填、内部字段可选。 |
