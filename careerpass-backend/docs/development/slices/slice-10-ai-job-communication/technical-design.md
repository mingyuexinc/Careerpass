# S10 AI 求职沟通技术设计

> 本文档记录 S10 当前锁定的 Agent 执行骨架、接口、Tool、状态和交接契约。
>
> 业务目标、业务规则和验收标准以同目录的 [`slice-spec.md`](./slice-spec.md) 为准；跨前后端业务事实以业务基线 `BF-RULE-045` 至 `BF-RULE-057` 为准。

## 1. 文档职责与交付关联

| 内容 | 事实源 |
| --- | --- |
| Slice 目标、范围和业务规则 | [`slice-spec.md`](./slice-spec.md) |
| 跨前后端业务事实 | [`../../../../docs/business/business-baseline.md`](../../../../docs/business/business-baseline.md) |
| 跨端契约 | [`../../../../docs/integration/slices/slice-10-ai-job-communication/integration-contract.md`](../../../../docs/integration/slices/slice-10-ai-job-communication/integration-contract.md) |
| 演示场景 | [`IS-S10-01`](../../../../docs/integration/slices/slice-10-ai-job-communication/integration-scenario.md)、[`IS-S10-02`](../../../../docs/integration/slices/slice-10-ai-job-communication/integration-scenario-s10-02.md)、[`IS-S10-03`](../../../../docs/integration/slices/slice-10-ai-job-communication/integration-scenario-s10-03.md) |
| 领域模型 | [`../../domain/domain-model.md`](../../domain/domain-model.md) |
| 数据库设计 | [`../../data/database-design.md`](../../data/database-design.md) |
| Agent 架构边界 | [`../../architecture/agent-workflow-architecture.md`](../../architecture/agent-workflow-architecture.md) |

| 项目 | 当前约定 |
| --- | --- |
| Integration Scenario | `IS-S10-01`、`IS-S10-02` |
| Integration Contract | `IC-S10-AI-COMMUNICATION@0.5`，状态 `locked` |
| 后端状态 | S10-01、S10-02、S10-03 `implemented` |
| 跨端交付状态 | S10-01、S10-02、S10-03 `integration_delivered` |
| 当前技术设计状态 | S10-01、S10-02、S10-03 `closed` |

当前文档承接已完成交付的 S10-01、S10-02、S10-03；S10-03 使用扩展 AgentTurn，不新增 Query 表；主动轮次允许没有 HR `source_message_id`，通过 `result_message_id` 关联可见 Agent 消息，幂等键为 `application_id + conversation_id + goal_condition_signature`。

S10-01 不新增通用 Agent 平台或 LangChain；S10-02 不使用 LLM、文件正文、OCR 或 Embedding，使用确定性资料匹配 Service/Repository 和现有消息事务能力。

## 2. 统一 Agent 执行骨架

### 2.1 总体流程

```text
触发入口
  → 身份、Application 和 Conversation 归属校验
  → 加载当前投递上下文快照
  → 读取当前 Conversation 历史作为上下文
  → 场景识别与确定性前置判断
  → Agent 生成结构化行动计划
  → Pydantic Schema 校验与业务规则校验
  → 调用已注册 Tool / Service
  → 再次校验 Tool 结果和副作用边界
  → 在单一事务中幂等写入消息、附件元数据和 Agent Turn 结果
  → 消息通道发送或形成受控失败
  → 记录最小不可见审计
```

Agent 不直接访问 ORM Session、Repository、对象存储或消息表。Agent 只输出结构化的场景选择、检索意图、回复草稿或判断建议；Workflow/Service 负责授权复核、业务判断、事务和副作用。

### 2.2 统一触发类型

| 触发类型 | 来源 | 允许场景 | 说明 |
| --- | --- | --- | --- |
| `hr_message_received` | HR 当前 Conversation 新消息 | S10-01、S10-02、S10-03 回答处理 | 先持久化并校验 HR 消息，再进入 Agent Turn |
| `proactive_query_start` | HR 进入当前 Application Conversation 后的 S10 Agent/Workflow 入口 | S10-03 | 先读取当前 Conversation 历史，再读取 JobGoal 和 JD；没有可提问条件时不产生消息，同一未确认条件最多生成一个 query |
| `agent_retry` | 同一 Agent Turn 的有限重试 | 原失败场景 | 必须复用原幂等键，不创建第二个业务结果 |

### 2.3 统一上下文

Agent Turn 只接收资源标识和最小脱敏上下文，不接收文件路径、完整简历原文、对象存储定位或模型原始响应。

| 上下文 | 读取范围 | 用途 |
| --- | --- | --- |
| 当前身份 | 当前 HR 与 Application 的授权关系 | 归属和可见性校验 |
| Application | 当前岗位、Candidate、AgentRunContext 关系 | 锁定投递边界 |
| Resume / CandidateProfile | S-07 启动时绑定的简历及其结构化投影 | S10-01 证据回答 |
| CandidateDocument | 当前 Candidate 的附加求职资料 | S10-02 附件交付 |
| JobGoal | 当前求职过滤条件 | S10-03 条件识别 |
| ParsedJobDescriptionSnapshot | 当前岗位已校验的结构化 JD | S10-03 缺口识别 |
| Conversation | 当前 Application 的历史消息 | 上下文、query 和回答关联；不覆盖 Resume 事实 |

### 2.4 场景路由与结果

| 场景 | Agent 负责 | 确定性 Service/Workflow 负责 | 成功结果 |
| --- | --- | --- | --- |
| S10-01 | 识别简历相关问题、形成检索意图和回答草稿 | Resume 证据授权、事实支持校验；经历范围完整但未出现目标能力时允许受控否定回答；消息写入 | Agent 文本消息 |
| S10-02 | 识别资料类型或名称 | CandidateDocument 归属校验、附件准备、下载能力和消息写入 | 带可下载附件的 Agent 消息 |
| S10-03 主动提问 | 从过滤条件识别待核验条件并生成二元 query | 已过滤条件排除、JD 缺口判断、query 幂等、消息写入 | Agent query 消息 |
| S10-03 回答判断 | 将 HR 回复解析为二元结果 | 求职目标判断和沟通行为写入 | “好的，了解”或“感谢沟通，当前不考虑这个岗位了” |

## 3. 接口与 Handoff Contract

### 3.1 HR 消息入口

```text
POST /api/v1/applications/{application_id}/conversation/messages
```

调用方为当前 Application 下有权访问的 HR。服务端从身份上下文确定发送主体，不接受客户端传入的 Candidate、Job、Conversation 归属作为授权依据。

请求的业务字段：

```json
{
  "conversation_id": "uuid",
  "client_message_id": "string",
  "content": "HR 的消息内容"
}
```

约束：`content` 为非空文本；`conversation_id` 必须属于 `application_id`；`client_message_id` 在当前身份和 Conversation 内幂等；不接受文件路径、对象键或外部 URL。

成功响应使用统一 `{code, msg, data}` 包络，返回本次接收消息、Agent Turn 状态和本次新增的可见消息。响应不返回简历原文、模型原始响应、内部文件定位或其它 Conversation。Conversation ID 由 S-08 在 Application 创建时初始化，并由 HR 会话列表返回。

### 3.1.1 HR 会话列表

```text
GET /api/v1/applications/hr/current/conversations
```

只返回当前 HR 所有未删除岗位下当前首轮 Application 的 Conversation 安全投影和 `sent` 消息。

### 3.2 Conversation 消息读取

```text
GET /api/v1/applications/{application_id}/conversation/messages?conversation_id={conversation_id}
```

只返回当前 HR 有权访问的当前 Application Conversation 消息；S10-02 可在消息内返回安全附件投影。不返回内部审计、Prompt、工具输入、检索证据摘要、文件正文或其它岗位会话。

### 3.3 附件下载（S10-02）

```text
GET /api/v1/applications/{application_id}/conversation/messages/{message_id}/attachments/{attachment_id}/download
```

服务端复核当前 HR → Job → Application → Conversation → Message → Attachment 的完整归属链，并确认附件仍处于创建后 7 天有效期内，以受控下载响应返回文件。HR 不需要额外确认或重新登录即可重复下载；该接口只支持下载，不提供在线预览接口；不得返回对象存储路径、内部对象键或长期有效的公开 URL。CandidateDocument 删除不影响有效期内的已发送附件。

### 3.4 Agent Turn 内部交接

统一 Agent Workflow 接收以下内部交接，不作为 HR 可直接调用的公开 API：

| 项目 | 约定 |
| --- | --- |
| Producer | Conversation Message Service 或 S10 调度入口 |
| Consumer | S10 Agent Workflow |
| 触发条件 | HR 消息已通过归属校验，或 S10-03 主动 query 入口已满足前置条件 |
| 输入 | `application_id`、`conversation_id`、`trigger_type`、`source_message_id`、`idempotency_key` |
| 输出 | `AgentTurnResult`，包含场景、状态、结果类型和新增消息标识 |
| 身份与归属 | Service 在执行前重新校验，不信任 Producer 单独提供的权限结论 |
| 幂等 | 同一 `idempotency_key` 复用已有 Agent Turn 结果 |
| 版本 | `AGENT-TURN@0.1` |

S-08 通过 `APPLICATION-CONVERSATION@0.1` 交接唯一 Conversation 容器。S10 只接收当前 Application 及其归属关系、S-07 绑定 Resume/Profile 和 Conversation 标识；S10 不接收或修改 Application 状态。

## 4. Tool 与结构化结果契约

### 4.1 Tool 边界

| Tool | 输入 | 输出 | 失败分类 | 副作用 |
| --- | --- | --- | --- | --- |
| `load_conversation_context` | Application、Conversation 标识 | 最小授权上下文 | `context_not_found`、`forbidden` | 无 |
| `retrieve_resume_evidence` | 当前 Application、问题检索意图 | 直接事实证据集 | `evidence_not_found`、`retrieval_failed` | 无 |
| `retrieve_candidate_document` | Candidate 归属、资料意图 | 资料元数据和可交付引用 | `document_not_found`、`retrieval_failed` | 无 |
| `prepare_downloadable_attachment` | 已授权 CandidateDocument、Message 关联 | 附件元数据和下载句柄 | `attachment_failed` | 准备附件，不直接发送消息 |
| `extract_goal_condition` | JobGoal 过滤条件 | 结构化求职条件 | `semantic_extraction_failed` | 无 |
| `detect_jd_gap` | 求职条件、已校验 JD | 单一缺口或无缺口 | `validation_failed` | 无 |
| `parse_binary_answer` | 原问题、HR 当前或后续回复 | `yes` 或 `no` | `answer_parse_failed` | 无 |

Tool 输入由 Pydantic 校验；Tool 不接收 SQL、Shell、ORM Session、对象路径或未经验证的外部 URL。Tool 失败不能直接驱动消息、Application 状态或其它副作用。

S10-02 的 `retrieve_candidate_document` 只读取当前 CandidateDocument 的安全元数据和文件名，不读取文件正文；资料意图通过明确请求语句提取资料名称，再结合文件名标准化、关键词和受控别名进行确定性匹配。证书、照片、证明等常用类别使用受控别名，未预置类别（例如“学籍验证报告”）直接使用请求名称与文件名匹配。主演示 Fixture 保证每次请求只有一个符合项；匹配成功后只创建一个 MessageAttachment。

### 4.2 Agent 结构化输出

Agent 输出必须符合受限 Schema，至少包含：

```json
{
  "scene": "resume_answer | document_delivery | goal_query | goal_judgement",
  "intent": "string",
  "tool_calls": [],
  "draft_message": "string|null",
  "binary_answer": "yes|no|null",
  "confidence": "high|low"
}
```

`scene`、`tool_calls`、`binary_answer` 和 `draft_message` 由业务校验共同约束：不允许 Agent 自行选择未注册 Tool；S10-03 只将“是/不是”“对/不对”“属于/不属于”等明确二元表达归一为 `yes/no`，带额外说明时只提取其中的二元答案；`binary_answer` 不是 `yes/no` 时不得形成推进判断；任何输出不得直接修改 Application。

S10-02 匹配成功时 `draft_message` 和持久化 Agent Message 的 `content` 必须为空字符串；附件卡片是唯一用户可见结果，不发送“已为你找到”等成功提示语。

### 4.3 Agent Turn 结果

```json
{
  "turn_status": "completed | waiting | failed",
  "outcome": "message_sent | attachment_sent | query_sent | continue | stop | pending | no_reply | tool_failed",
  "scene": "resume_answer | document_delivery | goal_query | goal_judgement",
  "message_ids": ["uuid"],
  "retryable": false
}
```

`waiting/pending` 只表示 S10-03 query 尚未完成判断；`failed/tool_failed` 不等于业务上停止推进。客户端不得把 Agent Turn 结果直接映射为 Application 状态。

## 5. 状态、幂等与事务

### 5.1 状态契约

| 对象 | 状态 | 状态拥有者 | 合法迁移 |
| --- | --- | --- | --- |
| AgentTurn | `accepted`、`processing`、`completed`、`waiting`、`failed` | Agent Workflow Service | `accepted → processing → completed/waiting/failed` |
| Message | `pending`、`sent`、`failed` | Conversation Message Service | `pending → sent/failed` |
| MessageAttachment | `preparing`、`downloadable`、`failed`、`expired` | Attachment Service | `preparing → downloadable/failed`；`downloadable → expired`（创建后 7 天） |
| S10-03 query 语义 | `not_created`、`awaiting_answer`、`judged`、`pending` | Agent Workflow Service | `not_created → awaiting_answer → judged`；未识别到有效二元答案时保持 `pending`，后续明确二元答案可由 `pending → judged`；`pending` 不是终态 |

Conversation 本身当前不新增独立业务状态；Agent 编排状态不等于 Application 或 AgentRunContext 状态。

### 5.2 幂等键

| 场景 | 幂等边界 | 重复处理 |
| --- | --- | --- |
| HR 入站消息 | `conversation_id + client_message_id` | 返回已有入站消息和 Agent Turn 结果 |
| S10-01 | 入站消息关联的 Agent Turn | 复用已有回答，不重复追加 Agent 消息 |
| S10-02 | `application_id + conversation_id + source_message_id + document_intent` | 复用已有 Agent 消息和一个附件，不重复发送 |
| S10-03 query | `application_id + conversation_id + goal_condition_signature`，并以当前 Conversation 历史复核 | 同一未确认条件最多保留一个 query；重复进入或重复触发不重复追加问题 |

### 5.3 事务边界

1. Message Service 在短事务中校验归属、写入 HR 入站消息并认领 Agent Turn 幂等键。
2. Agent/Tool 执行在事务外完成；外部模型调用不占用数据库事务。
3. 结果通过结构化和业务校验后，在一个短事务中写入 Agent Message、Attachment 元数据和 Agent Turn 结果。
4. 只有消息和附件元数据提交成功且消息状态为 `sent` 时，HR 才能读取或下载；失败事务不得留下可见的半成品 Agent 消息。

## 6. 场景失败、重试和安全边界

| 场景 | 失败处理 | 是否追加 Agent 消息 |
| --- | --- | --- |
| S10-01 事实范围完整且未出现目标能力 | 发送受控否定回答，例如“没有大模型训练相关经历” | 是，否定事实消息 |
| S10-01 检索/生成/校验失败，消息通道可用 | 有限重试；仍失败时发送受控模板“暂时无法回答当前问题” | 是，模板消息 |
| S10-01 消息通道不可用或发送重试耗尽 | 记录失败，不追加兜底消息 | 否 |
| S10-02 资料附件准备或消息发送失败 | 有限重试；仍失败视为 Tool 调用失败 | 否 |
| S10-02 资料匹配成功 | 写入 `content` 为空的 Agent Message 和一个 `MessageAttachment`；前端只展示附件卡片 | 是，仅附件 |
| S10-02 未找到或资料失效 | 返回友好受控 Agent 文本，不暴露文件状态、正文或内部定位 | 是，仅文本消息；不追加附件 |
| S10-02 附件过期 | 下载返回受控失败；历史消息保留安全元数据 | 否，不重新创建附件 |
| S10-03 HR 未回答 | query 保持等待，不主动追问 | 否 |
| S10-03 没有可提问条件 | 静默结束，不创建 query | 否 |
| S10-03 HR 回复解析失败 | 视为没有有效回复；不判断继续/停止，query 保持待处理，不发送额外提示 | 否 |
| S10-03 解析失败后再次收到明确二元答案 | 将后续明确答案视为原 query 的有效回答并继续判断 | 继续或停止时是 |
| S10-03 重复触发 | 根据当前 Conversation 历史复用已有业务结果或静默结束 | 否，不重复追加 query |
| S10-03 判断为继续推进 | 写入固定沟通回复 | 是，“好的，了解” |
| S10-03 判断为停止推进 | 写入固定沟通回复 | 是，“感谢沟通，当前不考虑这个岗位了” |

默认自动重试为首次尝试加最多 2 次重试；重试必须复用幂等键，不得重复产生消息或附件。具体退避时长属于实现配置，不改变契约语义。

日志、审计和 LangSmith 追踪只允许记录 `application_id`、`conversation_id`、Agent Turn 标识、场景、阶段、状态、失败分类、耗时和重试次数。不得记录简历原文、联系方式、消息原文、文件正文、对象存储定位、Prompt 或模型原始响应。

## 7. 领域与数据影响

### 7.1 实体使用

| 实体 | 用途 | 读写变化 | 归属/授权 |
| --- | --- | --- | --- |
| `Application` | 锁定当前投递上下文 | 仅查询 | HR → Job → Application；S10 不修改状态 |
| `AgentRunContext` | 读取当前运行和 S-07 绑定关系 | 仅查询 | Candidate 归属 |
| `Resume` / `CandidateProfile` | S10-01 事实和证据 | 仅查询 | 当前 AgentRunContext 绑定 |
| `CandidateDocument` | S10-02 资料来源 | 仅查询 | 当前 Candidate 归属 |
| `JobGoal` | S10-03 求职条件 | 仅查询 | 当前 Candidate 当前目标 |
| `ParsedJobDescriptionSnapshot` | S10-03 JD 信息 | 仅查询 | 当前 Job 归属和 Application 关系 |
| `Conversation` / `Message` | 沟通会话和正式消息 | 创建 / 查询 | Conversation 属于 Application；Message 属于 Conversation |
| `MessageAttachment` | 可下载附件元数据 | 创建 / 查询 | Attachment 属于 Message，来源 CandidateDocument |
| `AgentTurn` | Agent 执行幂等、状态和最小结果 | 创建 / 更新 | 属于当前 Conversation，不作为 Application 状态 |

### 7.2 数据库影响

- 当前增量已实现 `conversations`、`messages` 和 `agent_turns`，迁移为 `20260820_0015`；`message_attachments` 已由迁移 `20260820_0016`、Repository 和真实下载联调落地；S10-03 AgentTurn 主动轮次扩展由迁移 `20260821_0017` 落地。
- `Application`、`AgentRunContext`、`JobGoal`、Resume、CandidateProfile、CandidateDocument 和 JD 快照不新增 S10 业务字段。
- `MessageAttachment` 保存下载所需的安全元数据、来源 CandidateDocument 关系、有效期和独立下载引用，不保存文件正文或内部对象定位作为 API 响应；有效期内不依赖 CandidateDocument 当前记录才能下载。
- `AgentTurn` 只保存幂等键、场景、状态、结果分类和脱敏失败信息，不保存 Prompt、模型原始响应或消息原文。
- 事务和约束以本设计 5.3 和 5.2 为准；S10-01 消息边界和 S10-02 附件元数据、独立保留、下载链路均已在 Verify/Close 中确认。

### 7.3 全局事实同步

- 业务基线已同步 `BF-RULE-045` 至 `BF-RULE-057`。
- 领域模型和数据库设计已将 `MessageAttachment` 更新为 `implemented`；其来源引用、有效期和下载对象交接按迁移 `20260820_0016` 执行。

## 8. Readiness、实现边界与验证

### 8.1 依赖

| 依赖 | 用途 | 当前状态 |
| --- | --- | --- |
| 现有认证与当前身份 | HR/Application/资源归属校验 | 已有能力，待 S10 接入验证 |
| PostgreSQL | Conversation、Message、Attachment、AgentTurn 持久化 | S10-01/S10-02/S10-03 已完成迁移和联调验证 |
| CandidateDocument 对象存储 | 附件下载和 7 天独立保留 | 已验证删除交接、重复下载和过期清理引用保护 |
| Qwen Plus HTTP 适配 | S10-01 基于 Resume-derived facts 的结构化回答 | 代码已接入；2026-08-20 脱敏结构化事实最小真实调用通过 |
| Agent Workflow 运行模块 | 统一执行骨架 | 当前尚未实现 |

S10-01 后端统一预检已完成并记录；本次代码不据此扩大 Docker、Compose 或外部服务的可用性结论。

Readiness 证据（2026-08-20）：从后端根目录执行 `scripts/backend-readiness.ps1`。受限上下文首次结果为 `execution_denied`；按门禁在授权执行上下文复跑后，Docker CLI、Engine、Compose、`desktop-linux` context 和项目 Compose 配置均为 `ready/valid`。该预检为只读检查，未启动或修改容器。

跨 Slice Handoff 证据（2026-08-20）：开发者已完成 S-08 → S10 前后端联调，确认 `APPLICATION-CONVERSATION@0.1` 的唯一 `conversation_id` 可由 HR 会话列表消费，首次消息列表为空且不生成欢迎消息。该证据已关闭 Handoff 依赖。

### 8.2 实现边界

- API 层：解析请求、当前身份、统一响应和下载响应，不编排 Agent 业务。
- Service 层：Conversation/Message/Attachment/AgentTurn 用例编排、权限复核、状态和事务。
- Agent/Workflow 层：场景路由、结构化计划、Tool 编排和结果校验，不直接持久化。
- Tool 层：固定输入 Schema、超时、有限重试和脱敏错误；不接受 SQL、Shell 或内部路径。
- Repository 层：所有 Conversation、Message、Attachment、AgentTurn 及既有资源查询和写入。
- Infrastructure 层：LLM、对象存储和消息传输适配，不拥有业务状态。

### 8.3 验证计划

| 验证层 | 最小覆盖 |
| --- | --- |
| 单元 | 场景路由、事实来源优先级、二元回答、状态迁移、失败分类和幂等键 |
| Slice Integration | 当前 Application 归属、Conversation/Message/Attachment/AgentTurn 事务和重复请求 |
| Capability Acceptance | S10-01 既有验收；S10-02 文件名语义匹配、单附件消息、幂等、下载/过期、跨 Application 复用和敏感信息边界 |
| Cross-Slice | S-08 交接的绑定 Resume、JobGoal、JD 快照和 Application 关系 |
| E2E | HR 进入当前投递沟通、查看 Agent 消息、下载附件和完成 S10-03 闭环 |

### 8.4 S10-01 Verify/Close 证据

- PostgreSQL 集成：`tests/integration/test_s10_communication.py` 通过，覆盖 S-08 Application → Conversation 幂等初始化、HR 归属链、跨 Application 隔离、事实回答、经历范围内的否定回答、无事实模板、Qwen 失败、重复和并发 `client_message_id`，以及安全事实投影。
- Capability Acceptance：从 `careerpass-backend` 执行 `uv run pytest tests/acceptance/s10_01_communication -m capability_acceptance -o addopts='-q'`，结果 `1 passed`。
- 前端真实路径：受控 HR 登录后进入 `/hr/conversations`，首个空会话可见；真实发送“你的工作经历中有包括大模型训练吗？”得到明确无相关经历的 Agent 回答，技能问题得到正式 Agent 回答，超范围出生地问题得到受控模板；页面未显示 fact_refs、Prompt、模型原始响应或内部定位。
- 回归：前端 `npm run typecheck` 通过，`npm test -- --run` 通过（20 files / 65 tests）；后端 S10 相关单元和 PostgreSQL 集成通过。统一后端全量单元回归中 15 个既有临时目录测试受当前 Shell 的 `C:\Users\...\Temp\pytest-of-*` 权限限制，非 S10 失败。
- 真实 Qwen 证据与确定性 Capability Acceptance 分离：真实调用只验证外部能力和脱敏边界；固定 Fixture 验收不依赖外部模型，且不保存 Prompt、原始响应或敏感原值。

### 8.5 S10-02 Verify/Close 记录

- 业务基线、Slice Spec、领域/数据设计和 `IC-S10-AI-COMMUNICATION@0.5` 已锁定；
- `IS-S10-02`、固定文件名 Fixture、验收命令和 Artifact 路径已建立；
- 文件名确定性匹配不依赖 LLM，S05 → S10 CandidateDocument 交接边界已确认；
- PostgreSQL `MessageAttachment` 迁移、对象存储下载、7 天有效期和 CandidateDocument 删除交接已验证；
- 后端匹配、空正文单消息单附件、7 天有效期、删除交接、下载权限、跨 Application 复用和前端仿微信文件卡片已通过；`IS-S10-02` 已完成整改回归并标记为 `integration_delivered`。

### 8.6 S10-03 Verify/Close 记录

- Capability Acceptance 通过 13 项；前端 `npm run typecheck` 和 `conversationsPage.test.tsx` 通过。
- 开发者重启后端后完成真实前端场景复测：有缺口时发送唯一 query，无条件时静默，未回答/解析失败不追问，后续明确二元回答完成原 query，继续/停止回复、重复触发去重、权限隔离和状态不变均符合 Contract。
- 运行数据库已应用迁移 `20260821_0017`；主动 query 入口返回 HTTP 200，重复触发复用同一 AgentTurn，不重复追加消息。
- 已整改运行数据库未迁移导致的 404，以及主动 query 响应读取未预加载附件导致的 500；回归后 `IS-S10-03` 标记为 `integration_delivered`。

## 9. 设计锁定与回退

- 本技术设计锁定统一 Agent Turn、场景路由、Tool 边界、消息/附件状态、幂等、失败和审计语义。
- API 字段、消息状态、附件下载能力、Conversation 归属或 Application 影响范围变化时，必须回退到 Slice Design，并同步业务基线、Integration Contract 和 Scenario。
- S10-02 不依赖 LLM；对象存储、消息链路、数据库迁移和前端下载证据已写入 `IS-S10-02` Acceptance Artifact。
- 当前结论：S10 整体为 `integration_delivered`；S10-01、S10-02、S10-03 均已完成 Verify/Close。
