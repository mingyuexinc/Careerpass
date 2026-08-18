# 切片：S-06 求职目标创建 技术设计

> 状态：`implemented` / `integration_delivered`。S-06 只保存候选人的当前求职目标；S-07 负责 Agent 启动条件、启动事务和简历绑定。

## 1. 事实源与交付关联

- 业务事实：[`../../../../../docs/business/business-baseline.md`](../../../../../docs/business/business-baseline.md)
- Slice 规格：[`slice-spec.md`](slice-spec.md)
- Integration Contract：[`../../../../../docs/integration/slices/slice-06-job-goal/integration-contract.md`](../../../../../docs/integration/slices/slice-06-job-goal/integration-contract.md)
- Integration Scenario：[`../../../../../docs/integration/slices/slice-06-job-goal/integration-scenario.md`](../../../../../docs/integration/slices/slice-06-job-goal/integration-scenario.md)

| 项目 | 锁定值 |
| --- | --- |
| Scenario | `IS-S06-01` |
| Contract | `IC-S06-JOB-GOAL@0.1`，`locked` |
| Handoff | `JOB-GOAL-HANDOFF@0.1`，`locked` |
| 后端状态 | `implemented` |
| 跨端状态 | `integration_delivered` |

## 2. API 契约

### 2.1 查询当前目标

`GET /api/v1/job_goals/current`

响应：`{code, msg, data: {goal: JobGoal | null}}`。

### 2.2 创建或更新当前目标

`PUT /api/v1/job_goals/current`

请求：

```json
{
  "offer_target": 3,
  "title": "后端开发工程师",
  "filters": "优先 AI 应用"
}
```

约束：`offer_target` 为严格整数且范围 1–10；`title` 去首尾空白后非空；`filters` 去首尾空白后保存，可为空；请求禁止额外字段。

成功响应：

```json
{
  "code": 200,
  "msg": "job goal saved",
  "data": {"goal": {"id": "...", "offer_target": 3, "title": "后端开发工程师", "filters": "优先 AI 应用", "status": "active", "created_at": "...", "updated_at": "..."}}
}
```

错误语义：

| 场景 | HTTP / code | 结果 |
| --- | --- | --- |
| 请求字段非法 | 400 / `400` | 不写入，返回安全校验错误 |
| 未登录 | 401 / `401` | 不返回目标数据 |
| 非求职者身份 | 403 / `403` | 不返回目标数据 |
| `achieved` / `abandoned` 目标修改 | 409 / `409` | 保持原目标不变 |

服务端从 `CurrentIdentity` 获取 Candidate，不接受 `candidate_id`、`resume_id` 或 `job_id`。S-06 不读取、不绑定简历和 JD，不启动 Agent，不创建异步任务。

## 3. 数据与状态

新增 `job_goals` 表：

| 字段 | 约束 |
| --- | --- |
| `id` | UUID 主键 |
| `candidate_id` | 非空外键，唯一；一个 Candidate 只有一个当前目标 |
| `offer_target` | 非空，数据库 CHECK 约束 1–10 |
| `title` | 非空字符串 |
| `filters` | 非空文本，空文本表示未填写 |
| `status` | `active`、`achieved`、`abandoned` |
| `created_at` / `updated_at` | 带时区时间 |

S-06 仅创建或更新 `active` 目标。目标为 `achieved` 或 `abandoned` 时拒绝修改；Agent 运行中的冻结由 S-07 的运行上下文状态负责，S-06 不伪造该状态。

S-07 实现 AgentRunContext 后，S-06 的 `PUT /api/v1/job_goals/current` 必须通过 Repository 查询当前 Candidate 是否已有 `running` 或 `finished` 运行上下文；存在时返回既定 `409 / PRECONDITION_NOT_MET`。前端禁用编辑只改善交互，不能替代该服务端校验。S-07 的回归验证必须覆盖 S-06 的目标更新拒绝路径。

事务边界为一次 `GET/PUT` 请求内的 Repository 事务；数据库唯一约束和 Service 状态检查共同保证重复保存不产生第二个当前目标。

## 4. 分层实现

```text
JobGoalPage → jobGoalApi → API Controller → JobGoalService → JobGoalRepository → PostgreSQL
```

- Controller：身份校验、Pydantic 请求解析和统一响应。
- Service：字段语义、状态锁定和用例编排。
- Repository：按当前 Candidate 查询、创建、更新和事务持久化。
- 前端：`jobGoalApi.ts` 负责 snake_case/camelCase 映射；登录后使用真实 API，未登录预览继续使用 Mock。

## 5. Readiness 与验证

- 后端统一预检：已通过，Docker/Compose/Engine 可用。
- PostgreSQL 迁移：新增 S-06 revision，必须在集成环境执行 `alembic upgrade head`。
- 测试数据：无目标、已有 active、已有 achieved/abandoned 目标；不要求简历/JD。
- 单元/API/数据库集成测试覆盖：创建、查询、更新、重复保存、字段校验、角色拒绝、终态拒绝和无简历/JD保存。
- 前端场景覆盖：真实登录后任务页调用 GET/PUT；刷新回显目标；保存不触发 Agent 启动。

## 6. 交接契约

`JOB-GOAL-HANDOFF@0.1`：S-07 通过 `GET /api/v1/job_goals/current` 获取当前 Candidate 的 `active` 目标；目标数据不含简历绑定。S-07 在自己的启动事务中读取目标、当前简历和画像，并创建运行上下文；S-08 负责在匹配前读取和校验可用结构化 JD。

## 7. 实现级验证与开发者交付

- 实现级验证已完成：API、迁移、后端单元回归、S-06 专项测试、前端测试、类型检查和生产构建均已执行。
- `IS-S06-01` 的第 4 节演示验证结果、问题整改和关闭结论必须由开发者填写；Coding Agent 不得代填。
- 开发者已完成前后端联调并裁定 `IS-S06-01` 为 `integration_delivered`。
- S-06 不产生 Agent 启动或简历绑定副作用；启动条件权威计算仍由 S-07 负责。
