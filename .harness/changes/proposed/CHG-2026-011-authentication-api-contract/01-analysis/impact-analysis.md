# 影响分析

## 受影响模块与边界

| 模块 | 影响 | 所有权/权限影响 | 备注 |
| --- | --- | --- | --- |
| 认证与会话管理 | 定义注册、登录和当前身份契约 | Access Token 必须经服务端验签与身份复核 | Refresh/登出为 Deferred |
| 候选人管理 | 建立 User 与 Candidate 一对一锚点 | 不允许客户端指定 `candidate_id` | 数据库唯一约束保证 |
| 后续候选人资源模块 | 统一取得可信当前身份 | 必须按 `candidate_id` 校验归属 | 不得只按资源 ID 授权 |

## 契约与数据影响

- API：新增/明确 `/api/v1/auth/register`、`/login`、`/me`；`/refresh`、`/logout` 不属于 MVP 实现。
- 数据库与 Alembic：审阅 `candidates.user_id` 唯一约束及其回滚顺序。
- Redis/Celery：无。
- LLM、Prompt、追踪脱敏：密码、Token 和哈希均不得写入。

## 风险与缓解

| 风险 | 等级 | 缓解措施 |
| --- | --- | --- |
| 用户与候选人关联不唯一 | high | 数据库唯一约束、原子创建与 Repository 复核。 |
| Token 或密码泄漏 | high | 最小响应、脱敏日志、短期 Access Token。 |
| 将 Deferred 接口误作为 MVP 前置 | medium | 在契约和范围文档中明确标记，不注册对应路由。 |
