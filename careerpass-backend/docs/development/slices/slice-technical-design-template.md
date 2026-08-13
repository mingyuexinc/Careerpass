# 切片：<Slice 名称> 技术设计

> 本文档只记录当前 Slice 的技术落地事实和证据。
>
> 业务目标、输入、输出、前置条件、业务规则、范围和验收标准以同目录的 `slice-spec.md` 为准。跨 Slice 的领域、数据库和业务事实以对应全局事实源为准。

## 1. 文档职责与事实源

### 1.1 本 Slice 技术事实

- Slice 规格：同目录的 `slice-spec.md`
- 跨前后端业务事实：[`../../../../docs/business/business-baseline.md`](../../../../docs/business/business-baseline.md)
- API、异步任务和 Handoff Contract：本文档
- 前后端 Integration Contract 与 Integration Scenario：[`../../../../docs/integration/README.md`](../../../../docs/integration/README.md) 及具体场景目录
- 领域模型：[`../../domain/domain-model.md`](../../domain/domain-model.md)
- 数据库设计：[`../../data/database-design.md`](../../data/database-design.md)
- 跨 Slice 业务规则：[`../../product/business-rules.md`](../../product/business-rules.md)
- 后端架构与开发规范：[`../../architecture/backend-architecture.md`](../../architecture/backend-architecture.md)、[`../backend-guidelines.md`](../backend-guidelines.md)

### 1.2 维护规则

- Slice Design 阶段锁定 API、异步任务、数据影响、Handoff Contract 和关键依赖。
- Implement 阶段只补充与已确认设计一致的实现方案和局部决策。
- Verify、Close 阶段补充验证证据和最终一致性结论。
- 业务范围、用户可观察结果、权限语义、状态语义或已锁定契约发生变化时，回退到 Slice Design；不得只修改本文档掩盖设计变化。
- 全局事实源只记录稳定的跨 Slice 事实；本文档不复制完整领域模型或数据库设计。
- 本文档不独立重新定义前端 Mock 或开发者演示目标；跨端字段、状态和错误引用 Integration Contract，真实演示、自测和整改引用 Integration Scenario。

## 1.3 交付关联

| 项目 | 约定 |
| --- | --- |
| Integration Scenario | `<场景 ID 和路径>` |
| Integration Contract | `<契约 ID、版本和路径>` |
| 后端状态 | `pending` / `implemented` / `backend_ready` |
| 跨端交付状态 | `draft` / `integration_blocked` / `integration_delivered` |
| 演示目标 | `<开发者需要执行的最小真实用户路径>` |

## 2. API、异步任务与交接契约

### 2.1 接口契约

#### <接口名称>

- 路径与方法：`<例如 POST /api/v1/example>`
- 调用方：`<用户 / 前端 / 下游 Slice>`
- 输入：`<业务输入和必要约束；详细字段可在此记录>`
- 成功结果：`<响应结构、状态和下游用途>`
- 失败结果：`<HTTP 状态、错误语义和安全边界>`
- 幂等与副作用：`<规则>`

### 2.2 异步任务契约

若本 Slice 不产生异步任务，写明：

> 本 Slice 不产生异步任务。

若产生异步任务，至少记录：

| 项目 | 约定 |
| --- | --- |
| 任务标识与版本 | `<task_type>` / `<version>` |
| Producer | `<产生任务的 Slice 或入口>` |
| Consumer | `<Dispatcher / Worker / 下游 Slice>` |
| 输入 | `<固定结构和敏感字段边界>` |
| 状态 | `<queued → running → succeeded / failed>` |
| 幂等 | `<幂等键和重复执行规则>` |
| 失败处理 | `<重试、终态和脱敏失败分类>` |

### 2.3 交接契约（Handoff Contract）

只有 Producer Slice 维护跨 Slice 交接契约；Consumer 只引用 Producer 的相同标识和版本。

| 项目 | 约定 |
| --- | --- |
| Producer | `<当前 Slice>` |
| Consumer | `<下游 Slice>` |
| 触发条件 | `<何时可交接>` |
| 输入 | `<Producer 已确认的输入>` |
| 输出 | `<下游可消费的业务结果>` |
| 身份与归属 | `<服务端可复核的归属链>` |
| 状态与幂等 | `<状态、重复交接和失败规则>` |
| 版本 | `<contract version>` |

## 3. 领域实体与数据影响

### 3.1 实体使用

只登记本 Slice 实际查询、创建、修改或作为运行时上下文使用的实体，不复制全局领域模型。

| 实体 | 本 Slice 用途 | 读写变化 | 归属/授权 | 全局事实源 | 处理结果 |
| --- | --- | --- | --- | --- | --- |
| `<实体>` | `<用途>` | `<查询 / 创建 / 修改 / 仅作上下文>` | `<归属链>` | [`domain-model.md`](../../domain/domain-model.md) | `<无变化 / 已同步 / 待回退>` |

### 3.2 数据库影响

- 新增或修改的表、字段、关系、约束和索引：`<无 / 具体变化>`
- Alembic 迁移：`<无新增迁移 / revision>`
- 事务边界：`<本 Slice 的原子范围>`
- 数据库事实源：[`database-design.md`](../../data/database-design.md)
- 若没有同步全局数据库文档，说明理由：`<理由>`

### 3.3 状态与业务规则同步

- 状态和合法迁移：`<无 / 具体状态与迁移>`
- 跨 Slice 业务规则：[`business-rules.md`](../../product/business-rules.md)
- 本 Slice 新增或改变的全局事实：`<无 / 已同步内容>`

## 4. 技术实现方案

### 4.1 分层与调用链

```text
<入口>
  → <请求/任务校验>
  → <Service 或用例编排>
  → <Repository / Infrastructure>
  → <结果、状态或交接>
```

### 4.2 实现边界

- API 层：`<职责>`
- Service 层：`<职责>`
- Repository 层：`<职责>`
- Infrastructure / 外部能力：`<职责或无>`
- 前端或下游消费：`<消费方式>`

### 4.3 局部实现决策

只记录影响理解、维护或验证的局部决策；普通命名、函数拆分和等价写法使用实现决策 Skill 自主选择，不在此展开。

| 决策 | 选择 | 简短理由 |
| --- | --- | --- |
| `<局部技术决策>` | `<选择>` | `<与现有代码一致、改动最小或复杂度最低>` |

## 5. 外部依赖、失败处理与安全边界

### 5.1 依赖与证据

| 依赖 | 用途 | 真实证据 | 状态 |
| --- | --- | --- | --- |
| `<依赖>` | `<用途>` | `<测试、运行验证或事实源>` | `<已确认 / blocked / 不适用>` |

### 5.2 失败处理

- 输入或业务校验失败：`<处理>`
- 资源不存在或无权访问：`<处理>`
- 外部依赖失败：`<处理>`
- 重试、幂等和终态：`<处理或不适用>`
- 不可逆副作用：`<授权、审计或不适用>`

### 5.3 敏感信息

- 不得进入响应、日志或追踪的内容：`<内容>`
- 脱敏诊断字段：`<关联 ID、阶段、状态、耗时等>`
- Prompt、任务输入和外部请求边界：`<规则或不适用>`

## 6. 实现决策记录

### 6.1 开发者需裁决事项

`<None. 或记录真正需要开发者裁定的问题、选项、推荐和最终决策>`

### 6.2 设计变化与回退

| 发现的变化 | 影响 | 回退 Gate | 处理结果 |
| --- | --- | --- | --- |
| `<变化或无>` | `<产品、契约、数据、架构或实现>` | `<Slice Design / Readiness Check / Implement / Verify>` | `<结果>` |

## 7. 验证结果与关闭结论

### 7.1 验证证据

| 验证类型 | 覆盖内容 | 结果 | 证据 |
| --- | --- | --- | --- |
| 单元验证 | `<规则或组件>` | `<通过 / 失败 / 不适用>` | `<测试或记录>` |
| API / 集成验证 | `<成功、失败、权限、幂等和数据一致性>` | `<结果>` | `<测试或记录>` |
| 前后端联调 | `<用户可观察闭环>` | `<结果>` | `<测试或记录>` |
| 外部能力验证 | `<真实依赖>` | `<结果 / 不适用>` | `<证据>` |

### 7.2 关闭结论

- `slice-spec.md` 与最终实现一致：`<是 / 否>`
- 本文档与代码、迁移和测试一致：`<是 / 否>`
- 全局领域、数据和业务事实已同步：`<是 / 否 / 不适用>`
- Handoff Contract 可供下游使用：`<是 / 否 / 不适用>`
- Integration Contract 与前端 Mock、真实 API 一致：`<是 / 否>`
- Integration Scenario 演示步骤通过：`<是 / 否>`
- Integration Scenario 问题已整改并完成回归：`<是 / 否 / 不适用>`
- 未决开发者裁决：`<无 / 具体事项>`
- 最终结论：`<Backend Ready / Integration Delivered / blocked>`
