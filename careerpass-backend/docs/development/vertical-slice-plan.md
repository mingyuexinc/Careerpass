# 垂直切片开发计划

> 文档目的：根据版本范围、能力映射和差距分析，确定业务闭环 Slice 的候选范围、依赖和开发顺序。
>
> 本文档只负责总体计划，不重复定义 Slice 边界规则、API Contract、领域/数据设计和实现细节。

## 1. 依据与规则

| 文档 | 用途 |
| --- | --- |
| `docs/product/backend-delivery-scope.md` | 版本范围和延期能力 |
| `docs/product/backend-capability-map.md` | 前端流程与后端能力映射 |
| `docs/development/backend-gap-analysis.md` | 当前证据、差距和阻塞 |
| `docs/decisions/backend-development-decisions.md` | Slice 拆分、Contract-First、架构边界和验证原则 |
| `../../../docs/integration/README.md` | Integration Contract、Integration Scenario 和跨端交付状态 |
| `../../../docs/business/business-baseline.md` | 跨前后端已确认的业务事实和待裁决事项 |

Slice 拆分原则直接以 `backend-development-decisions.md` 第 4 节为准：以业务闭环拆分，不以技术模块拆分；共享能力随首次真实使用最小实现；每个 Slice 只解决一个主要业务结果，并覆盖该结果所需的完整路径。

## 2. 切片进入条件

候选 Slice 通过 Slice Select 前，必须先阅读 [`../../../docs/business/business-baseline.md`](../../../docs/business/business-baseline.md)，并完成以下检查：

| 检查项 | 通过标准 |
| --- | --- |
| 业务结果 | 有明确、可观察且可独立验收的主要结果 |
| 链路闭合 | Trigger 到结果所需的业务链路已识别 |
| 独立验收 | 可独立定义业务规格、技术设计、Contract、验证和 E2E |
| 单一目标 | 不包含多个可独立验收的主要结果 |
| 边界冻结 | Scope、依赖和非目标可以确认 |
| 业务事实 | 依赖的业务事实均为 `confirmed`，受影响的 `pending` 事项已有裁决 |
| 交付场景 | 至少一个 Integration Scenario 已明确目标、演示数据和预期结果 |

任一检查未通过，Slice Select 保持 `blocked`。详细 Scope、Contract、权限、状态、数据、异步任务和 Definition of Done 在 Slice Design 中确认，关键技术与外部证据在 Readiness Check 中确认。

Slice 是实现边界，Integration Scenario 是交付边界，二者不要求一一对应。一个 Slice 可以支持多个场景，多个 Slice 也可以共同完成一个场景。

### 2.1 项目级基础服务基线

首个 Slice Select 前必须完成一次项目级基础服务基线预检，不把 PostgreSQL、Redis、Docker Compose、Alembic、Backend 健康检查和前端开发服务器验证推迟到某个 Slice 的实现末期。预检通过后，后续 Slice 只需在基础环境或关键依赖发生变化时重跑；Slice 特有的真实依赖仍在自身 Readiness Check 中确认，业务链路真实联调在 Verify 中完成。诊断路径和可复用结果统一记录在 [`backend-troubleshooting.md`](backend-troubleshooting.md)。

## 3. 切片卡片模板

| 字段 | 内容 |
| --- | --- |
| Slice ID/名称 | 使用业务结果命名 |
| Trigger | 用户操作、受控命令、任务或状态事件 |
| 主要业务结果 | 一个可观察、可重复验收的结果 |
| Scope | 本 Slice 解决的业务范围 |
| Non-goals | 不做、延期或归属其他 Slice 的内容 |
| 依赖 | 前置业务结果或已确认能力 |
| 状态 | `pending`、`partial`、`ready` 或 `blocked` |

单个 Slice 使用 [`slice-spec-template.md`](slices/slice-spec-template.md) 建立 `slice-spec.md`，使用 [`slice-technical-design-template.md`](slices/slice-technical-design-template.md) 建立 `technical-design.md`。前者只记录业务规格，后者记录 API、异步任务、Handoff Contract、数据影响、实现方案和验证证据；两份文档共同按 Slice Select、Slice Design、Readiness Check、Implement、Verify、Close 六阶段推进。

## 4. 后端切片拆分

以下拆分依据当前前端主流程、后端交付范围、能力映射和 Gap Analysis；具体 Slice 进入 Slice Design 后，再确认其最终 Scope、Contract 和验收边界。

| Slice | Trigger | 主要业务结果 | 依赖 | 当前状态 |
| --- | --- | --- | --- | --- |
| [S-01 用户登录](slices/slice-01-user-login/slice-spec.md) | 用户提交用户名和密码 | 返回认证结果和最小身份信息 | 无 | `ready` |
| S-02 岗位 JD 上传 | 受控导入命令或经裁决的岗位输入 | 形成已校验、可供抽取的岗位 JD 输入资源 | S-01；G4 范围 | `pending` |
| S-03 JD 信息抽取 | S-02 建立可抽取的岗位 JD 输入 | 形成可供下游查询的结构化、已解析岗位/JD 快照 | S-02（Handoff Contract：可抽取 JD 输入已建立） | `missing` |
| S-04 简历上传与解析 | 求职者上传正式简历 | 候选人获得可供后续流程使用的结构化画像 | S-01；对象存储；异步解析 | `partial` |
| S-05 求职者资料上传 | 求职者上传附加求职资料 | 候选人获得已保存、可在授权沟通中引用的资料资源 | S-01；对象存储 | `partial` |
| S-06 求职目标创建 | 求职者提交求职目标 | 当前候选人获得一个可用的活跃求职目标快照 | S-03、S-04 | `missing` |
| S-07 Agent 投递启动 | 求职者点击启动 Agent | Agent 从未启动进入运行中，形成后续自动求职流程的稳定执行入口 | S-03、S-04、S-06 | `missing` |
| S-08 岗位匹配与投递 | Agent 运行入口成立后执行匹配 | 系统生成结构化、可解释的匹配结果，并为成功匹配岗位创建系统内投递记录 | S-07（Handoff Contract：Agent 已进入运行中） | `missing` |
| S-09 投递进度更新 | HR 更新一条授权投递记录 | 投递记录进入合法后续阶段，候选人可看到进度变化 | S-08 | `missing` |
| S-10 AI 求职沟通 | HR 在授权投递上下文中查看或发送消息 | 系统形成会话和经过校验的回复草稿或模拟回复 | S-08、S-05；Agent 控制面最小能力 | `missing` |
| S-11 业务资料删除 | 已授权用户选择一条简历、求职资料或岗位 JD 并提交删除 | 指定资料按资源类型的删除条件从当前可用资料中移除，并处理下游引用和对象清理 | S-01、S-02、S-04、S-05；资源状态与引用规则 | `missing` |

Controller、Repository、Parser、Dispatcher、LLM Client、异步任务或数据库迁移不单独构成 Slice，随首次产生业务结果的 Slice 交付。

## 5. 顺序与变更规则

### 5.1 推荐顺序

```text
S-01 用户登录
  ├─> S-02 岗位 JD 上传 → S-03 JD 信息抽取 ─┐
  ├─> S-04 简历上传与解析 ──────────────────┼─> S-06 求职目标创建
  └─> S-05 求职者资料上传 ───────────────┐  │
                                         └──┘
S-06 求职目标创建 + S-03 + S-04
  → S-07 Agent 投递启动
  → S-08 岗位匹配与投递
  ├─> S-09 投递进度更新
  └─> S-10 AI 求职沟通（可引用 S-05）
资源创建完成后（S-02、S-04、S-05）
  └─> S-11 业务资料删除

S-08、S-09、S-10、S-11
  → Integration Scenario 驱动的前端闭环验收
```

S-11 可在对应资源创建后进入 Slice Select，不要求等待全部下游 Slice 完成；但简历、求职资料和岗位 JD 的删除条件、当前使用状态和下游引用处理必须在同一个 Slice Contract 中锁定。实际顺序以前置 Gate、真实能力证据和 Slice Design 结果为准，不按代码目录或技术组件排序。

### 5.2 变更回退

| 变化 | 回退位置 |
| --- | --- |
| 改变版本能力、角色或外部副作用 | `backend-delivery-scope.md` |
| 改变 Slice 用户结果或范围 | Slice Scope |
| 改变 API 字段、状态或语义 | 对应 Slice 的 `technical-design.md`，并回退 Slice Design |
| 改变资源归属、状态拥有者或数据边界 | 领域/状态/数据设计 |
| 发现链路无法闭合或无法 E2E | 重新执行 Slice 进入检查 |
| 真实前端演示失败 | 在 Integration Scenario 记录问题，按问题类型回退 Slice Design、Readiness Check、Implement 或 Verify |

## 6. 当前计划状态

本文件只确认候选 Slice、总体依赖、交付场景关联和计划规则，不裁决 G4 岗位来源等 Slice 内问题，也不把历史开发包转换为任务清单。

S-01 已完成身份模型裁决：`User` 是统一认证主体，Candidate 与 HR 是可挂载的业务身份，角色关联用于校验登录工作区上下文。具体业务资源授权不属于登录 Slice 的隐含范围。S-01 Readiness 为 `ready`，下一步进入 Implement。
