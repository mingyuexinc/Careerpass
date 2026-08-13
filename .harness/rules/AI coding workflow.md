# AI 编码工作流

## 1. 适用范围

本文件只指导 AI 如何执行前端优先、Slice 层级的编码工作，不定义业务、架构、接口、数据或环境事实。

AI 必须先读取根 AGENTS.md、`docs/business/business-baseline.md`、`docs/business/business-fact-extraction.md`、目标子工程 AGENTS.md 和当前 Slice 相关事实源，再按以下 Gate 串行工作。

遇到实现细节争议时，使用 `.harness/skills/implementation-decision-autonomy/实现决策自主权.md` 判断是否需要人工确认。开发者负责产品意图、业务边界、输入输出、核心约束和关键技术方向；Coding Agent 在不改变这些内容的前提下自主完成局部实现设计。

## 2. 六阶段门禁

| Stage | AI 工作 | Gate | 产物 |
| --- | --- | --- | --- |
| Slice Select | 从前端流程和 Slice 计划选择一个业务闭环，并指定交付场景 | 边界清晰，前置 Slice 和至少一个 Integration Scenario 已明确 | Slice 标识 + Scenario 标识 |
| Slice Design | 完成业务规格、技术设计和跨端契约，锁定数据变化、依赖和验收 | 无关键歧义，Integration Contract 已锁定或明确 blocked | `slice-spec.md` + `technical-design.md` + Integration Contract/Scenario |
| Readiness Check | 核对技术问题、演示数据、环境、真实外部证据和全局文档同步 | 全部满足或明确 blocked | Ready |
| Implement | 按已批准设计实现完整纵向链路 | 不偏离设计与红线 | 可运行代码 |
| Verify | 验证成功、失败、业务规则和真实前端演示场景 | 既定验收和 Integration Scenario 通过 | 测试/自测/问题整改/回归结果 |
| Close | 对齐文档、实现、契约、场景和证据 | 无遗留阻断项，场景达到 `integration_delivered` | Slice Done + Integration Delivered |

当前 Gate 未通过不得进入下一阶段。已有代码、历史归档、Mock 或任务清单不能替代前置 Gate。

## 2.1 项目级基础服务基线预检

项目级基础服务预检不属于六个 Slice Gate，但必须在首个 Slice Select 前完成；后续 Slice 只有在运行环境、数据库和关键基础服务发生变化时才重新执行。预检至少确认：

- Docker CLI、Docker Engine 和 Compose 可用；
- PostgreSQL、Redis 及其健康检查通过；
- Alembic 迁移可执行并达到当前 head；
- Backend 可启动，`/health/live` 和 `/health/ready` 返回成功；
- 前端开发服务器可启动并能访问 Backend 代理入口。

预检输出必须记录可复用的命令、结果和阻塞项。预检未通过时，不进入 Slice Implement；若问题只影响某个 Slice 的新增依赖，则在该 Slice 的 Readiness Check 中补充真实证据。

## 3. 选择 Slice

- 确认 Slice ID、Trigger、唯一主要业务结果、Scope、Non-goals 和稳定结束点。
- 列出依赖的业务事实编号；影响当前 Slice 的 `pending` 事实必须先裁决。
- 核对上游 Slice 已产生可依赖结果，下游 Handoff 可以明确。
- 若包含第二个可独立验收结果或依赖未定义胶水，保持 blocked。
- 为本 Slice 指定至少一个 Integration Scenario，明确开发者要演示的角色、操作、演示数据和用户可观察结果。

## 4. 设计 Slice

同时维护同一 Slice 目录下的 `slice-spec.md` 和 `technical-design.md`：

- `slice-spec.md` 只补全 Goal、Input、Output、Preconditions、Business Rules、Scope / Non-goals、Technical Constraints、Acceptance Criteria 和 Developer Decisions Required；
- `slice-spec.md` 引用跨前后端业务基线中的事实编号，不重复定义已确认的业务规则；
- `technical-design.md` 补全 API、异步任务、状态、错误、幂等、数据影响、前置 Slice、Producer、Consumer、Handoff Contract、技术方案、外部依赖、失败处理和验证证据；
- Integration Contract 记录前后端共同遵守的请求、响应、状态、错误和版本；Integration Scenario 记录演示目标、演示数据、步骤、预期结果和交付状态；
- `slice-spec.md` 不写 API 路径、JSON、数据库表、类名、方法名或实现流程；
- 技术设计只记录当前 Slice 如何使用全局事实源及对其产生的变化，不复制完整领域模型、数据库设计或跨 Slice 业务规则。

Producer Slice 的 Handoff Contract 章节是跨 Slice 交接契约唯一来源，Consumer 只引用相同 ID 和版本。跨端 Integration Contract 和 Integration Scenario 位于 `docs/integration/`，不得在 `.harness` 建立契约注册表。

## 5. 就绪检查

- 引用已通过的项目级基础服务基线预检；若基础服务状态发生变化，先重新执行预检。
- 确认 `slice-spec.md` 和 `technical-design.md` 不存在影响实现的未决范围、授权、接口、数据或状态问题。
- 确认所有影响当前 Slice 的业务事实均为 `confirmed`，或已有明确开发者裁决。
- 首次使用的 LLM、第三方 API、队列或其他关键依赖必须有最小真实证据。
- 影响实现的领域、数据、架构和外部能力事实已同步到对应子工程文档；技术设计只保留引用和本 Slice 的影响记录。
- 验收环境、测试数据、Repository 边界、统一响应、状态合法性和安全红线可执行。
- 演示账号、演示数据、真实前端入口和场景步骤可执行；前端 Mock、HTTP 适配器和后端 API 使用同一 Contract。

任一关键项不满足时标记 blocked，不开始编码。

## 6. 实现

- 只实现通过 Readiness Check 的 Slice。
- 前端 Mock 和后端实现都必须遵守已锁定的 Integration Contract，不得用 Mock 补充未裁决的后端事实。
- 完成入口、Service、Repository、数据、任务和可观察结果的完整链路。
- 资源访问必须校验当前身份和归属。
- LLM 输出必须结构化并经业务校验。
- 任务必须可追踪、幂等并有明确终态。
- 日志、追踪和响应不得暴露凭证、敏感原文、内部路径或模型原始响应。

发现设计变化时停止受影响实现并回退。

## 7. 验证与关闭

Verify 至少覆盖成功路径、非法输入、资源不存在、无权访问、依赖失败、状态迁移、幂等和数据一致性，并执行真实 Integration Scenario。Mock 不能替代真实前端联调或真实外部证据。

Close 前确认 `slice-spec.md` 仍只包含业务内容，`technical-design.md` 与最终实现一致，Integration Contract 与前后端实现一致，Integration Scenario 已记录自测、问题整改和回归结果，全局事实源已同步、验证可追溯、延期项明确且下游 Handoff 可用；实现没有产生未记录的跨前后端业务事实。

## 8. 回退

| 变化 | 回退 |
| --- | --- |
| Goal、边界、主要结果或前置 Slice | Slice Select |
| 规则、授权、契约、数据、状态、验收或跨 Slice 责任 | Slice Design |
| 关键依赖、技术路线、真实证据或全局同步 | Readiness Check |
| 不影响设计的实现缺陷 | Implement |
| 不影响设计的验证缺口 | Verify |

Verify 失败后，必须在 Integration Scenario 中记录问题。`contract_mismatch`、`business_scope_error` 或权限/状态/数据边界变化回退 Slice Design；关键环境或依赖问题回退 Readiness Check；普通代码问题回退 Implement；验证记录缺失回退 Verify。整改完成后必须重新执行受影响场景。

AI 不得自行批准 Gate；开发者负责关键范围、授权、副作用和 Gate 结论。
