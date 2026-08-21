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
| 状态 | `pending`、`partial`、`ready`、`implemented` 或 `blocked` |

单个 Slice 使用 [`slice-spec-template.md`](slices/slice-spec-template.md) 建立 `slice-spec.md`，使用 [`slice-technical-design-template.md`](slices/slice-technical-design-template.md) 建立 `technical-design.md`。前者只记录业务规格，后者记录 API、异步任务、Handoff Contract、数据影响、实现方案和验证证据；两份文档共同按 Slice Select、Slice Design、Readiness Check、Implement、Verify、Close 六阶段推进。

## 4. 后端切片拆分

以下拆分依据当前前端主流程、后端交付范围、能力映射和 Gap Analysis；具体 Slice 进入 Slice Design 后，再确认其最终 Scope、Contract 和验收边界。

| Slice | Trigger | 主要业务结果 | 依赖 | 当前状态 |
| --- | --- | --- | --- | --- |
| [S-01 用户登录](slices/slice-01-user-login/slice-spec.md) | 用户提交用户名和密码 | 返回认证结果和最小身份信息 | 无 | `ready` |
| S-02 岗位 JD 上传 | 受控导入命令或经裁决的岗位输入 | 形成已校验、可供抽取的岗位 JD 输入资源 | S-01；G4 范围 | `implemented` |
| S-03 JD 信息抽取 | S-02 建立可抽取的岗位 JD 输入 | 按固定 Markdown 标题形成以 `fields` 为主要交付结果、可供下游查询的结构化岗位/JD 快照 | S-02（Handoff Contract：可抽取 JD 输入已建立） | `implemented` |
| S-04 简历上传与解析 | 求职者上传 PDF 格式正式简历 | 候选人获得结构化画像及独立的岗位匹配资格判定 | S-01；对象存储；异步解析 | `implemented` |
| S-05 求职者资料上传 | 求职者上传附加求职资料 | 候选人获得已保存、可在授权沟通中引用的资料资源 | S-01；对象存储 | `implemented` |
| S-06 求职目标创建 | 求职者提交求职目标 | 当前候选人获得一个不绑定简历、可更新的活跃求职目标 | S-01 | `implemented` |
| S-07 Agent 投递启动 | 求职者点击启动 Agent | 校验当前目标、当前简历和画像匹配资格，绑定当前简历并从未启动进入运行中 | S-04、S-06 | `implemented` |
| S-08 岗位匹配与投递 | Agent 运行入口成立后执行匹配 | 同步检查关联 HR 的全部可用结构化 JD（岗位池最多 20 个），使用本地简化算法生成结构化、可解释的 Match，并为成功匹配岗位创建 Application 和初始 ProgressEvent | S-03、S-07（Handoff Contract：Agent 已进入运行中） | `implemented` |
| [S-09 投递进度更新](slices/slice-09-application-progress-update/slice-spec.md) | HR 更新一条授权投递记录 | 投递记录进入合法后续阶段，候选人可看到进度变化 | S-08 | `implemented` |
| S-10 AI 求职沟通 | HR 在授权投递上下文中查看或发送消息 | S10-01、S10-02、S10-03 已完成当前范围内交付 | S-08、S-05；Agent 控制面和资料下载最小能力 | `S10-01/S10-02/S10-03 integration_delivered` |
| S-11 业务资料删除 | 已授权用户选择一条简历、求职资料或岗位 JD 并提交删除 | 指定资料按资源类型的删除条件从当前可用资料中移除，并处理下游引用和对象清理 | S-01、S-02、S-04、S-05；资源状态与引用规则 | `integration_delivered` |

Controller、Repository、Parser、Dispatcher、LLM Client、异步任务或数据库迁移不单独构成 Slice，随首次产生业务结果的 Slice 交付。

## 5. 顺序与变更规则

### 5.1 推荐顺序

```text
S-01 用户登录
  ├─> S-02 岗位 JD 上传 → S-03 JD 信息抽取 ─┐
  ├─> S-04 简历上传与解析 ────────────────┼─> S-07 Agent 投递启动
  ├─> S-05 求职者资料上传                  │
  └─> S-06 求职目标创建（可与 S-02/S-03/S-04 并行） ┘
  → S-08 岗位匹配与投递
  ├─> S-09 投递进度更新
  └─> S-10 AI 求职沟通（可引用 S-05）
资源创建完成后（S-02、S-04、S-05）
  └─> S-11 业务资料删除

S-08、S-09、S-10、S-11
  → Integration Scenario 驱动的前端闭环验收
```

S-05 的业务裁决已确认：支持 PDF、Markdown、JPG 和 PNG 附加资料，单文件不超过 10 MB；支持批量上传并按文件独立处理；重复上传按幂等成功处理；上传状态按 `ready → success` 或 `ready → failed` 表达。上传和资料创建归属 S-05，删除归属 S-11；S-05 不主动暴露原文件，后续 Agent 检索和向 S-10 的授权交接由后续流程负责。S-05 的 Contract、真实前端联调和失败提示整改已完成，`IS-S05-01` 已标记为 `integration_delivered`；S-05 交付结果为 `implemented`。

S-11 可在对应资源创建后进入 Slice Select，不要求等待全部下游 Slice 完成；简历、求职资料和岗位 JD 的删除条件、逻辑移除语义、当前使用状态和下游引用处理已由业务基线确认，必须在同一个 Slice Contract 中表达并通过引用场景验证。实际顺序以前置 Gate、真实能力证据和 Slice Design 结果为准，不按代码目录或技术组件排序。

S-11 已完成 Slice Select、Slice Design、Implement、Verify 和 Close，当前状态为 `integration_delivered`：三类资源统一逻辑移除；简历仅在解析任务进入 `succeeded/failed` 终态且 Agent 尚未启动时可移除，`matching_ready/not_ready` 不改变资格，新上传的不同内容简历自动成为当前简历，解析未完成时仍不能启动 Agent；CandidateDocument 成功保存后可在 Agent 各生命周期阶段移除，删除后不参与新的资料检索，已创建附件保留 7 天；岗位 JD 仍只允许在解析终态且匹配尚未开始时移除。三份 S-11 Scenario 均已完成开发者验收并补齐脱敏结果证据，S11 交付目标达成。

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

S-04 已完成代码开发、真实解析链路验证、固定 PDF Capability Acceptance 和开发者最小演示验收；`IS-S04-01` 已标记为 `integration_delivered`。S-04 交付结果为 `implemented`，S-07 消费其已校验画像和匹配资格；S-06 不依赖 S-04。

S-05 已完成批量资料上传代码开发、权限/幂等/部分成功验证、真实前后端联调及失败提示整改复测；`IS-S05-01` 已标记为 `integration_delivered`。S-05 交付结果为 `implemented`，资料删除仍由后续 S-11 负责。

S-06 已完成目标 API、数据库迁移、前端真实 API 适配、实现级验证和前后端联调；开发者已将 `IS-S06-01` 裁定为 `integration_delivered`，S-06 求职目标创建交付成功。S-06 代码结果为 `implemented`，启动条件、Agent 运行上下文和启动时简历绑定仍由 S-07 负责。

S-07 已完成 Agent 启动上下文、启动 API、S-06 目标冻结联动、前端创建/查看子页面和前后端联调；开发者已将 `IS-S07-01` 裁定为 `integration_delivered`，S-07 代码结果为 `implemented`。S-07 只负责启动校验、当前简历绑定和进入 `running`；结构化 JD 检查、匹配和投递由 S-08 负责。

S-08 已完成 Match/Application/ProgressEvent 迁移、v0.1 确定性算法、S-07 同步编排、Application 查询 API 和 Candidate 进度页真实数据接入；开发者已完成真实前后端闭环复测，前述问题均已整改并通过验收。`IS-S08-01` 已标记为 `integration_delivered`，S-08 交付完成；其输出的 `APPLICATION-CONVERSATION@0.1` 已进一步完成 S-08 → S10 前后端联调复验。

S-09 已完成业务裁决、Slice Spec、Technical Design、Integration Contract 和 Integration Scenario；代码、前端真实 API 接入、原始 JD 文件名恢复、自动化验证、完整前后端演示和隔离 PostgreSQL 联调已完成，`IS-S09-01` 标记为 `integration_delivered`。S-09 复用现有 Application、ProgressEvent、Job、CandidateProfile、AgentRunContext 和 JobGoal，不新增业务实体或业务表；岗位文件名元数据由 `20260819_0014` 迁移落地。

S10-01 已由开发者裁定交付完成，锁定 `IC-S10-AI-COMMUNICATION@0.4` 中兼容的 S10-01 字段、`IS-S10-01` 和 S-08 `APPLICATION-CONVERSATION@0.1` 交接，完成 Qwen Plus 脱敏结构化事实最小真实调用、Conversation/Message/AgentTurn 持久化、权限/幂等/失败验证和真实前端联调。已补充“经历范围内的否定事实”语义：个人简历能覆盖经历范围但没有目标能力时，回答“没有相关经历”；资料范围不足时仍返回受控模板。已确认 S-08 成功创建 Application 后在同一事务内幂等初始化 Conversation，且该 Handoff 已完成开发者前后端联调复验；`IS-S10-01` 已标记为 `integration_delivered`。S10-02 的文件名确定性语义匹配、单 Agent 消息单附件、7 天有效期、删除后的独立下载、跨 Application 复用、无 LLM 内容读取、迁移 `20260820_0016`、PostgreSQL/对象存储联调和仿微信文件卡片整改已通过；`IS-S10-02` 已标记为 `integration_delivered`。S10-03 已新增 `IC-S10-AI-COMMUNICATION@0.5`、`IS-S10-03`、AgentTurn 主动轮次扩展、迁移 `20260821_0017`、主动触发 API/前端入口、二元解析和能力验收；开发者重启后端完成真实场景复测，`IS-S10-03` 已标记为 `integration_delivered`，S10-3 Verify/Close 完成。通用 Agent Workflow 平台仍为后续范围。

S-11 已完成三类业务资料删除的真实前后端验收：开发者重建并启动 S11 迁移、Backend、Worker 和 Dispatcher，验证 HR 岗位 JD 删除返回成功且从刷新后的列表消失；简历、附加资料、当前简历指针、逻辑删除过滤、审计幂等、S10-02 附件保留和前端删除交互均通过自动化回归与 Scenario 验收。`IS-S11-01`、`IS-S11-02`、`IS-S11-03` 均已标记为 `integration_delivered`。
