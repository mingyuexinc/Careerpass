# Integration Contract：S-06 求职目标创建

> Contract ID：`IC-S06-JOB-GOAL@0.1`。状态：`locked`。

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| Slice | `S-06` |
| Scenario | [`IS-S06-01`](integration-scenario.md) |
| Producer | S-06 后端求职目标能力 |
| Consumer | 求职者任务配置页 |
| 交付边界 | 当前目标查询、创建和 Agent 启动前更新 |

## 2. API

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/api/v1/job_goals/current` | 查询当前候选人的目标 |
| PUT | `/api/v1/job_goals/current` | 创建或更新同一个当前目标 |

请求字段：`offer_target: int`、`title: string`、`filters: string`。`offer_target` 为 1–10 严格整数；`title` 去首尾空白后必填；`filters` 可为空自由文本。请求不得包含 Candidate、Resume 或 Job 标识。

响应统一为 `{code, msg, data}`。查询数据为 `{goal: object | null}`；保存数据为 `{goal: object}`。目标投影包含 `id`、`offer_target`、`title`、`filters`、`status`、`created_at`、`updated_at`，不包含 `resume_id`。

## 3. 业务语义

- 保存不要求简历、画像或 JD。
- 保存只创建/更新当前目标，不启动 Agent，不绑定简历，不创建异步任务。
- 重复保存使用 `PUT current` 更新同一目标。
- `active` 目标可更新；`achieved` / `abandoned` 目标不可更新。
- Agent 运行中的冻结由 S-07 运行上下文负责；S-06 不判断或修改 Agent 状态。
- S-07 在启动事务中读取目标，并绑定启动时的当前简历。

## 4. 错误语义

| 场景 | HTTP | code |
| --- | ---: | ---: |
| 请求校验失败 | 400 | 400 |
| 未认证 | 401 | 401 |
| 非求职者身份 | 403 | 403 |
| 已进入不可修改终态 | 409 | 409 |

错误响应不包含目标敏感数据、简历正文、内部路径、令牌或 ORM 异常。

## 5. 版本与锁定记录

线上字段采用 snake_case；前端适配层映射为 camelCase。改变路径、字段含义或状态语义必须升级 Contract Major 版本并回退 Slice Design。

| 日期 | 变化 | 状态 |
| --- | --- | --- |
| 2026-08-16 | 锁定 API、字段、状态、权限、无简历绑定和 S-07 交接边界 | `locked` |
