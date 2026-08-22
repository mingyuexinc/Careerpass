# 切片：S-07 Agent 投递启动 技术设计

> 状态：`integration_delivered`。S-07 后端、迁移和 API Contract 保持不变；前端页面整改已完成并通过 `IS-S07-01` 页面联调。S-08 的匹配和投递实现不属于本 Slice。
>
> S-07 只负责启动条件校验、当前简历绑定、运行上下文创建和进入 `running`；S-08 负责结构化 JD 检查、匹配和投递记录。

## 1. 文档职责与事实源

- Slice 规格：[`slice-spec.md`](slice-spec.md)
- 跨前后端业务事实：[`../../../../../docs/business/business-baseline.md`](../../../../../docs/business/business-baseline.md)
- 前端页面设计：[`../../../../../careerpass-frontend/docs/development/slice-07-agent-start.md`](../../../../../careerpass-frontend/docs/development/slice-07-agent-start.md)
- Integration Contract：[`../../../../../docs/integration/slices/slice-07-agent-start/integration-contract.md`](../../../../../docs/integration/slices/slice-07-agent-start/integration-contract.md)
- Integration Scenario：[`../../../../../docs/integration/slices/slice-07-agent-start/integration-scenario.md`](../../../../../docs/integration/slices/slice-07-agent-start/integration-scenario.md)
- S-06 目标交接：`JOB-GOAL-HANDOFF@0.1`
- 领域模型：[`../../../domain/domain-model.md`](../../../domain/domain-model.md)
- 数据库设计：[`../../../data/database-design.md`](../../../data/database-design.md)

### 1.1 交付关联

| 项目 | 约定 |
| --- | --- |
| Integration Scenario | `IS-S07-01`，`integration_delivered` |
| Integration Contract | `IC-S07-AGENT-START@0.1`，`locked` |
| Handoff | `AGENT-RUNNING-HANDOFF@0.1`，`locked` |
| 后端状态 | `implemented_integration_verified` |
| 跨端交付状态 | `integration_delivered` |
| 演示目标 | 求职者在顶部菜单切换目标创建/查看子页面；创建页启动 Agent，查看页以列表行展示当前目标，不展示匹配资格或投递结果 |

## 2. API、异步任务与交接契约

### 2.1 查询当前目标

复用 S-06 已实现接口：

```text
GET /api/v1/job_goals/current
```

返回当前 Candidate 的安全目标投影。S-07 不创建第二套目标查询能力，不接受客户端 Candidate、Resume 或 Job 标识。

### 2.2 查询当前运行状态

```text
GET /api/v1/agent_runs/current
```

成功响应：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "state": "not_started",
    "can_start": true,
    "run": null
  }
}
```

`state` 只允许 `not_started`、`running`、`finished`；`can_start` 是不展开原因的布尔投影，`not_started` 不代表一定可启动。`run` 存在时只返回：

```json
{
  "id": "<uuid>",
  "status": "running",
  "started_at": "<iso-datetime>"
}
```

不得返回匹配资格、画像字段、简历原文、联系方式、结构化 JD、内部文件定位或模型响应。

### 2.3 启动当前 Agent

```text
POST /api/v1/agent_runs/current/start
```

请求体固定为空对象，禁止额外字段：

```json
{}
```

服务端从当前认证身份获取 Candidate，并在同一事务中重新校验当前目标、当前简历、画像和当前运行状态。成功响应：

```json
{
  "code": 200,
  "msg": "agent started",
  "data": {
    "run": {
      "id": "<uuid>",
      "status": "running",
      "started_at": "<iso-datetime>"
    }
  }
}
```

重复启动同一当前运行上下文返回相同成功结构，不创建第二个运行上下文。前端统一展示约定成功文案，不根据重复与首次启动切换用户文案。

错误投影：

| 场景 | HTTP / `code` | `msg` 语义 | `data` |
| --- | --- | --- | --- |
| 未登录 | `401 / 401` | 通用未授权 | `null` |
| 非求职者身份 | `403 / 403` | 通用无权访问 | `null` |
| 条件不满足或状态竞态 | `409 / 409` | 通用暂不可启动 | `null` |
| 其它服务端异常 | `500 / 500` | 通用服务异常 | `null` |

缺少目标、简历未解析成功、画像不可匹配、运行已存在或运行已结束不得通过错误响应暴露具体资格详情。正常前端路径通过 `can_start` 和页面状态阻止提交；竞态只显示通用提示并重新查询。

### 2.4 异步任务契约

本 Slice 不产生异步任务，不调用 Dispatcher、Worker、匹配服务或投递服务。S-08 是否异步调度由 S-08 自己的 Slice Design 决定。

### 2.5 Handoff Contract

Producer Slice 维护唯一交接契约；S-08 只引用本契约，不复制字段定义。

| 项目 | 约定 |
| --- | --- |
| Contract | `AGENT-RUNNING-HANDOFF@0.1` |
| Producer | S-07 |
| Consumer | S-08 |
| 触发条件 | `AgentRunContext` 在事务提交后为 `running` |
| 输出 | `run_id`、服务端可验证的 Candidate 归属、JobGoal 快照引用、绑定 Resume 引用、CandidateProfile 引用和 `running` 状态 |
| 传输边界 | 前端不接收完整交接对象；S-08 通过 `run_id` 在服务端按归属链读取受控上下文 |
| 身份与归属 | 服务端复核 Candidate、JobGoal、Resume、CandidateProfile 和运行上下文之间的归属关系 |
| 幂等 | 同一 `run_id` 只能形成一次启动交接；重复读取不得创建运行、匹配或投递记录 |
| 版本 | `AGENT-RUNNING-HANDOFF@0.1`，已锁定 |

S-08 在消费交接后才检查可用结构化 JD；没有可用 JD 不影响 S-07 的启动成功，但会影响 S-08 后续流程。

## 3. 领域实体与数据影响

| 实体 | 本 Slice 用途 | 读写变化 | 归属/授权 | 处理结果 |
| --- | --- | --- | --- | --- |
| JobGoal | 读取当前目标并作为启动快照来源 | 仅读取；不改变 `active/achieved/abandoned` | `CurrentIdentity → Candidate → JobGoal` | 复用 S-06 查询和 Repository |
| Resume | 读取启动时有效简历并绑定运行上下文 | 仅读取；不替换历史绑定 | `CurrentIdentity → Candidate → Resume` | 解析成功才可绑定 |
| CandidateProfile | 校验 `matching_ready` 并作为交接上下文 | 仅读取；不返回原值 | `Resume → CandidateProfile` 且复核 Candidate | 画像只作为服务端条件 |
| AgentRunContext | 表达当前 Agent 运行、目标快照和简历绑定 | 创建或幂等复用；S-07 只写 `running` | `CurrentIdentity → Candidate → AgentRunContext` | 新增 `agent_run_contexts`，状态由运行流程维护 |
| Match / Application | S-07 不创建 | 无变化 | 由 S-08 负责 | 不得由启动成功伪造 |

### 3.1 AgentRunContext 数据设计

本 Slice 设计锁定以下最小字段，具体 SQLAlchemy 类型和 Alembic revision 在 Implement 前落实：

| 字段 | 约束/用途 |
| --- | --- |
| `id` | UUID 主键，作为 `run_id` |
| `candidate_id` | 非空外键，运行上下文所有者 |
| `job_goal_id` | 非空外键，启动时目标快照来源 |
| `resume_id` | 非空外键，启动时绑定的简历 |
| `candidate_profile_id` | 非空外键，启动时校验并交接的画像 |
| `goal_snapshot` | JSONB 安全快照，仅保存目标业务字段，不保存敏感简历原文 |
| `status` | `running`、`finished`；S-07 只创建 `running` |
| `started_at` | 非空，首次启动时间；重复启动不刷新 |
| `finished_at` | 可空，由后续流程写入 |
| `created_at` | 非空，持久化时间 |

唯一性和索引：

- `UNIQUE(candidate_id, job_goal_id)`，保证当前目标不会产生第二个运行上下文；
- `INDEX(candidate_id, status)`，支持当前用户运行状态查询；
- `INDEX(resume_id)`，支持绑定关系审计和后续交接查询。

## 4. 事务与分层实现方案

### 4.1 分层与调用链

```text
前端任务页
  → GET 当前目标 / GET 当前运行状态
  → POST 当前 Agent 启动
  → Controller 校验身份和请求体
  → AgentStartService 读取并校验 Candidate-owned 目标、Resume、Profile 和运行状态
  → AgentRunRepository 在事务内创建或幂等读取 AgentRunContext
  → 返回 running，并提供 S-08 交接引用
```

### 4.2 事务边界

启动事务必须原子完成：

1. 获取当前服务端 Candidate 身份。
2. 按 Candidate 查询当前目标，并确认目标状态可启动。
3. 按 Candidate 查询启动时有效的解析成功简历及其画像。
4. 确认画像为 `matching_ready`；不检查结构化 JD。
5. 锁定或查询 Candidate 当前目标对应的运行上下文。
6. 若已存在 `running` 或 `finished` 上下文，按重复启动规则返回既有上下文或通用状态结果。
7. 创建目标快照、简历/画像绑定和 `running` 上下文。
8. 提交事务后才允许形成 S-08 交接引用。

并发冲突通过数据库唯一约束和事务内重读处理；失败时不得留下半成品绑定或运行上下文。

### 4.3 分层边界

- Controller：当前身份、请求体、统一响应和安全错误。
- Service：启动条件、目标冻结判断、重复启动和事务编排。
- Repository：按 Candidate 归属查询目标/简历/画像，锁定和持久化运行上下文；禁止 Service 直接访问 ORM Session。
- Infrastructure：本 Slice 无外部能力和异步任务。
- 前端：只消费 Contract 的安全投影，不自行决定启动事实。

### 4.4 S-06 联动

S-06 的目标保存接口必须在 AgentRunContext 为 `running` 或 `finished` 时拒绝更新当前目标。S-07 实现后需补充 S-06 的运行状态查询依赖和回归测试；这属于跨 Slice 数据一致性，不允许通过前端禁用按钮替代服务端校验。

## 5. 外部依赖、失败处理与安全边界

### 5.1 依赖与证据

| 依赖 | 用途 | 真实证据 | 状态 |
| --- | --- | --- | --- |
| S-01 身份 | 当前 Candidate 身份 | S-01 已交付 | 已确认 |
| S-04 简历与画像 | 解析状态、`matching_ready` 和 Candidate 归属 | S-04 已交付 | 已确认 |
| S-06 当前目标 | 目标查询和快照来源 | `IC-S06-JOB-GOAL@0.1`、`JOB-GOAL-HANDOFF@0.1` | 已确认 |
| PostgreSQL 迁移 | AgentRunContext 持久化和唯一性 | `20260817_0012` 已加入迁移链并在隔离 PostgreSQL 执行 | 已验证 |
| S-08 | 后续 JD 检查、匹配和投递 | `AGENT-RUNNING-HANDOFF@0.1` | 仅交接依赖，S-08 尚未实现 |

后端启动门禁记录：

| 项目 | 记录 |
| --- | --- |
| 故障案例匹配 | 未匹配新的既有案例；复用“Docker CLI 可发现但 Engine 连接需确认”诊断路径 |
| 统一预检命令 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend-readiness.ps1` |
| 执行上下文 | 后端目录；默认权限执行被拒绝，按文档使用授权执行 |
| 预检状态与时间 | 2026-08-17：启动本机 Docker Desktop 后，Client/Compose/Engine、`desktop-linux`、Compose 配置均通过，`status=ready` |

### 5.2 失败处理

- 正常页面只在条件满足时提交；服务端仍必须处理未授权、资源缺失、状态竞态和数据库冲突。
- 条件不满足或竞态返回统一 `409 / PRECONDITION_NOT_MET`，不返回具体匹配资格缺失原因。
- 重复启动当前 `running` 上下文返回幂等成功；`finished` 上下文不得开启新运行。
- 数据库唯一冲突必须转换为幂等读取或安全冲突，不能产生第二个上下文。
- S-07 不处理 JD 缺失、匹配失败、投递失败或投递记录重复。

### 5.3 敏感信息

- API、日志和追踪不得出现简历原文、联系方式、画像原值、内部文件定位、令牌和模型原始响应。
- 运行上下文只记录关联 ID、状态、阶段、耗时和受控失败分类。
- `goal_snapshot` 只保存目标字段；简历和画像通过受控资源引用读取，不复制敏感原值。

## 6. 实现决策记录

### 6.1 局部实现决策

| 决策 | 选择 | 理由 |
| --- | --- | --- |
| 当前运行状态查询 | `GET /api/v1/agent_runs/current` | 与 S-06 `current` 资源命名一致，支持刷新后恢复页面状态 |
| 启动命令 | `POST /api/v1/agent_runs/current/start`，空对象请求体 | 明确命令语义，禁止客户端提交资源标识，便于幂等重试 |
| 启动方式 | 同步事务创建运行上下文，不新增 S-07 异步任务 | S-07 的唯一结果是持久化 `running`，匹配和投递由 S-08 决定 |
| 运行上下文幂等性 | 当前运行上下文内重复启动不产生新运行；无投递 `no_match` 且岗位状态改善时允许创建下一轮 | 保留历史运行记录，不覆盖既有结果 |
| 页面成功投影 | 只返回运行摘要 | 满足页面状态恢复，避免暴露简历、画像和内部数据 |

### 6.2 开发者需裁决事项

无。业务范围、状态语义、用户可观察结果、交接边界和幂等语义已由当前裁决确定；以上为不改变这些事实的工程设计选择。

### 6.3 设计变化与回退

| 发现的变化 | 影响 | 回退 Gate | 处理结果 |
| --- | --- | --- | --- |
| S-07 启动前检查至少一个可匹配 JD | S-07/S-08 边界、启动条件和交接 | Slice Design | S-07 只做就绪门禁，岗位过滤、Match 和 Application 仍由 S-08 负责 |
| 前端不展示匹配资格详情 | 页面状态和响应投影 | Slice Design | 已同步前端页面、设计规范和 Contract |
| 启动成功不创建匹配/投递数据 | 数据实体和场景验收 | Slice Design | 已在 S-07 技术设计、Contract 和 Scenario 明确 |

## 7. Readiness Check 计划

Readiness 已通过，隔离 Compose 环境中的 PostgreSQL、Redis、Backend、Worker、Dispatcher 和迁移均可用：

| 检查项 | 最小证据 | 状态 |
| --- | --- | --- |
| 基础服务 | 后端统一预检、迁移达到 head、Backend/前端入口可用 | 通过；`status=ready`，迁移重复执行通过 |
| 有目标可启动数据 | 当前 Candidate、`active` 目标、解析成功简历、`matching_ready` 画像；不准备 JD 也可启动 | 通过真实 API 场景 |
| 不可启动数据 | 无目标、解析中/失败简历、`matching_not_ready` 画像 | 通过单元/集成覆盖 |
| 幂等数据 | 首次启动后的 `running` 上下文，重复 POST 和刷新均复用同一 ID | 通过真实 API 场景 |
| 终态数据 | `finished` 运行上下文，确认不能开启新运行 | 通过服务定向测试 |
| 权限数据 | HR 身份、未登录请求和其他 Candidate 资源隔离 | 通过真实 API 场景和集成测试 |
| Contract 示例 | 前端 Mock、HTTP Repository、后端 Schema 与本 Contract 一致 | 已完成代码核对 |
| S-06 回归 | Agent 运行中/结束后更新目标均被服务端拒绝 | 通过定向测试和真实运行中 API 场景 |
| UI 验收 | 页面级菜单、创建/查看子页面、列表行、目标只读和成功文案 | 已通过；三项前端整改已完成并回归 |

## 8. 验证结果与关闭结论

### 8.1 验证证据

| 验证类型 | 覆盖内容 | 结果 | 证据 |
| --- | --- | --- | --- |
| 单元验证 | 条件判断、状态投影、重复启动、上传边界和 S-06 冻结 | 通过 | `uv run --no-cache pytest --no-cov -q tests/unit` |
| 静态质量 | 后端 Ruff、前端 typecheck/lint/test/build | 通过 | `uv run --no-cache ruff check app alembic tests`；前端四项命令均通过 |
| API / 数据库集成 | 成功、未授权、条件不足、并发、重复启动和数据一致性 | 通过 | 隔离 Compose API/数据库场景；迁移重复执行通过 |
| 前后端联调 | 页面级菜单、创建/查看子页面、启动、刷新和只读锁定 | 已通过 | `IS-S07-01` 第 4 节；前端会话刷新恢复已补齐 |
| S-08 交接 | `running` 上下文可被下游按 `run_id` 读取 | Producer 通过 | 真实数据库存在唯一 `run_id`；S-08 消费实现留待其 Slice |

### 8.2 关闭结论

- 代码和迁移与本文档一致：已完成；
- 后端状态：`implemented_integration_verified`；
- 跨端状态：`integration_delivered`；
- `IS-S07-01` 开发者演示：菜单切换、目标列表、启动、刷新恢复、只读锁定和无投递结果已验证；
- 最终结论：S-07 已完成交付。整改只改变前端页面组织和会话恢复，不改变 S-07 后端 Contract、运行上下文和交接边界。
