# S-08 岗位匹配与投递技术设计

> 状态：`integration_delivered`；开发者已完成真实前后端演示复测，前述问题均已整改并通过验收。
>
> 本文档负责把业务算法和跨端 Contract 转换为可实现的后端边界；业务规则以 [`business-baseline.md`](../../../../../docs/business/business-baseline.md) 和 [`matching-algorithm-v0.1.md`](../../../../../docs/business/matching/matching-algorithm-v0.1.md) 为准。

## 1. 交付边界

S-08 由 S-07 启动成功后的后端内部服务同步执行。S-07 事务先提交运行上下文，随后 S-08 在独立事务中处理最多 20 个岗位。前端不提交匹配命令，只通过 Application 查询读取结果。每个成功创建的 Application 在同一 S-08 事务内幂等初始化一个 Conversation 容器，不写入欢迎消息；该容器通过 `APPLICATION-CONVERSATION@0.1` 交给 S10。

S-08 不使用 Celery、Redis、外部匹配服务或大模型。

## 2. 依赖与输入读取

| 输入 | 来源 | 使用方式 |
| --- | --- | --- |
| `AgentRunContext` | S-07 | Candidate、JobGoal、Resume、CandidateProfile 和目标快照的权威关联 |
| CandidateProfile | S-04 | 岗位经历、项目经历、技能、工作年限和层级判断字段；工作/项目 `highlights` 作为技能证据 |
| JobGoal 快照 | S-07 | 目标岗位名称和用户硬过滤条件；`offer_target` 不参与评分 |
| ParsedJobDescriptionSnapshot | S-03 | 五项核心 JD 字段；仅 `parse_succeeded + matching_ready` 可用 |
| Job | S-02 | 岗位归属、删除状态和岗位标识 |

Repository 必须在查询时校验 Candidate、AgentRun、JobGoal、Resume、CandidateProfile 和 Job 的归属关系。Service、算法模块和 Workflow 不直接访问 ORM Session。

## 3. v0.1 参数包

以下参数是 Coding Agent 在本版本锁定的确定性工程参数，不构成新的业务范围：

| 参数 | v0.1 值 |
| --- | --- |
| 各维度分值 | `0–100`，浮点数保留两位 |
| 岗位画像权重 | `0.35` |
| 能力层级权重 | `0.25` |
| 技能匹配权重 | `0.40` |
| 匹配阈值 | `60.00`，达到阈值即 `matched` |
| 最终展示分数 | 总分四舍五入为整数 `0–100` |
| 结果排序 | `total_score DESC`、`created_at ASC`、`job_id ASC` |
| 同分处理 | 按 Job UUID 字典序稳定排序 |

### 3.1 岗位画像

- 同一受控 AI 软件开发岗位族：`100`；
- 受控 AI 软件开发子族之间相关但名称不完全一致：`80`；
- 仅存在通用软件开发证据、缺少 AI 软件开发证据：`40`；
- 岗位本质方向明显不一致：`0`。

岗位画像不拥有独立否决权，仍参与加权总分。

### 3.2 能力层级

岗位和候选人分别归一化为 `low`、`mid`、`high`：

| 差异 | 分数 |
| --- | ---: |
| 同级 | `100` |
| 相差一级 | `60` |
| 相差两级 | `0` |

候选人级别使用职位、工作年限、工作经历范围和项目复杂度等结构化摘要判断；无法判断时使用 `mid` 作为受控 Demo 默认值，并在内部诊断记录中标记 `inferred`。

### 3.3 技能匹配

- 从 `responsibilities` 和 `requirements` 中只提取技能项；
- 候选人技能证据包括顶层 `skills`、项目 `technologies`、工作/项目 `highlights`，以及工作/项目标题和摘要中的明确技术事实；
- 工作年限、学历、证书、管理职责和层级描述不进入技能项；
- 技能同义词使用受控归一化表，例如 `大模型/LLM`、`Agent/智能体`、`Function Calling/函数调用`；
- `skill_score = matched_skill_count / required_skill_count × 100`；
- 没有可提取技能项或候选人无明确技能证据时，技能分数为 `0`；
- 技能缺失不单独淘汰岗位。

`Match.input_snapshot.algorithm_input.candidate` 必须保存实际使用的 `experience_highlights` 和 `project_highlights`，用于结果追溯；该输入扩展不新增数据库字段，沿用现有 JSONB 快照。

### 3.4 硬过滤

- 明确排除地点命中：`filtered_out`；
- 明确最低薪资不满足：`filtered_out`；
- `优先某地` 等软偏好忽略；
- 自由文本未识别出业务过滤语义时视为没有过滤条件；
- 不支持当前 AI 软件开发岗位族的岗位记录为 `filtered_out`。

### 3.5 推荐理由模板

推荐理由在 Match 创建时生成，不在查询时重算：

| 场景 | 模板方向 |
| --- | --- |
| 匹配成功 | `岗位画像{role_result}；能力层级{level_result}；技能匹配{skill_result}；综合匹配得分{score}。` |
| 分数不足 | `岗位画像{role_result}；能力层级{level_result}；技能匹配{skill_result}；综合得分{score}未达到匹配阈值。` |
| 硬过滤 | `岗位因{filter_reason}被排除，未进入匹配评分。` |

模板变量只使用脱敏后的岗位和候选人业务语义，不包含联系方式、原文、文件路径或模型原始响应。

## 4. 持久化设计

### 4.1 `matches`

| 字段 | 约束/含义 |
| --- | --- |
| `id` | UUID 主键 |
| `run_id` | 外键 → `agent_run_contexts.id` |
| `candidate_id` | 外键 → `candidates.id` |
| `job_id` | 外键 → `jobs.id` |
| `algorithm_version` | 固定 `v0.1` |
| `input_snapshot` | 已解析业务语义 JSONB，不保存原文 |
| `status` | `filtered_out`、`not_matched`、`matched`、`application_created` |
| `role_score`、`level_score`、`skill_score` | `0–100`，可空仅限 `filtered_out` |
| `total_score` | `0–100`，可空仅限 `filtered_out` |
| `recommendation_reason` | 脱敏规则模板文本 |
| `reason_code` | 过滤或未匹配的稳定分类码 |
| `created_at` | 创建时间 |

唯一约束：`UNIQUE(run_id, job_id)`；查询索引覆盖 `candidate_id`、`run_id` 和 `job_id`。

### 4.2 `applications`

| 字段 | 约束/含义 |
| --- | --- |
| `id` | UUID 主键 |
| `run_id` | 外键 → `agent_run_contexts.id` |
| `match_id` | 外键 → `matches.id`，唯一 |
| `candidate_id` | 外键 → `candidates.id` |
| `job_id` | 外键 → `jobs.id` |
| `status` | 初始为 `submitted`，后续由 S-09 状态机推进 |
| `applied_at` | 系统内投递记录创建时间 |
| `created_at`、`updated_at` | 审计时间 |

唯一约束：`UNIQUE(run_id, job_id)`。Application 不代表真实外部投递。

### 4.3 `progress_events`

S-08 至少写入一条 `application_created` 事件，记录 Application、Candidate、Job、操作者主体 `agent`、事件时间和前后状态。原文、联系方式和内部文件定位不得进入事件载荷。

## 5. 同步执行流程

```text
S-07 提交 AgentRunContext
  → S-08 查询关联 HR 的全部可用结构化 Job，最多 20 个
  → 对每个 run_id + job_id 做幂等检查
  → 硬过滤
  → 岗位族和混合岗位处理
  → 三维评分与加权总分
  → 持久化 Match
  → matched 结果创建 Application 和初始 ProgressEvent
  → 为 Application 幂等创建 Conversation 容器（`APPLICATION-CONVERSATION@0.1`）
  → 全部岗位完成后统计 Application
  → Application=0 时 AgentRun finished/no_match
```

同一批次内按稳定排序逐个处理。Match 和 Application 写入使用一个 S-08 数据库事务；重复调用只补处理缺失的岗位结果，不覆盖已有结果。

### 5.1 S10 Handoff Contract

| 项目 | 约定 |
| --- | --- |
| Producer | S-08 matching repository |
| Consumer | S10 Conversation Message Service |
| 触发条件 | Application 成功创建或重复确认 |
| 输出 | 唯一 `conversation_id` 容器；不写入欢迎消息 |
| 身份与归属 | `Application → Job → HrProfile` 与 `Application → Candidate → AgentRunContext` 可复核 |
| 状态与幂等 | `UNIQUE(conversations.application_id)`；重复执行复用已有 Conversation |
| 版本 | `APPLICATION-CONVERSATION@0.1` |

## 6. API 设计

### 6.1 启动并同步执行 S-08

沿用：

```text
POST /api/v1/agent_runs/current/start
```

请求体不增加匹配参数。服务端先完成 S-07 事务提交，再同步执行 S-08。响应数据至少包含：

```json
{
  "run": {
    "id": "uuid",
    "status": "running|finished",
    "started_at": "timestamp",
    "finished_at": "timestamp|null",
    "finish_reason": "offer_target_reached|no_match|null"
  }
}
```

### 6.2 查询当前 Candidate 的投递记录

新增：

```text
GET /api/v1/applications/current
```

响应数据至少包含：

```json
{
  "run": {
    "id": "uuid",
    "status": "running|finished",
    "finish_reason": "offer_target_reached|no_match|null"
  },
  "applications": [
    {
      "id": "uuid",
      "job_id": "uuid",
      "status": "submitted",
      "job_title": "AI 应用开发工程师",
      "company_name": "受控岗位展示字段",
      "location": "深圳",
      "salary": "25-40K",
      "match_score": 82,
      "recommendation_reason": "岗位画像匹配；能力层级接近；技能匹配度较高。",
      "applied_at": "timestamp"
    }
  ],
  "total": 1
}
```

接口只返回当前 Candidate 所属 Application，不返回 Match 列表。所有响应使用 `{code, msg, data}` 包装。

## 7. 安全、事务和日志

- 查询和写入必须经过 Candidate、Job、AgentRun 和关联 HR 归属校验；
- 算法模块不接收原始 JD、原始简历、文件路径或模型响应；
- 日志只记录 `run_id`、`job_id`、阶段、状态、耗时和失败分类；
- S-08 事务不得留下半条 Match 或无 Match 的 Application；
- 实现不新增异步任务，不进入 Celery/Redis 任务状态机。

## 8. 测试设计

### 单元测试

- 地点和薪资硬过滤；
- 软偏好和不可识别自由文本忽略；
- AI 软件开发岗位族、普通后端岗位和混合岗位；
- 同级、相差一级、相差两级能力层级；
- 技能同义词、技能覆盖率和无技能项；
- 加权补偿、阈值边界、稳定排序和推荐理由模板。

### Repository/Service 测试

- 输入快照和算法版本持久化；
- `run_id + job_id` 唯一约束；
- 20 个岗位逐个处理；
- 零 Application 时 `finished/no_match`；
- 重复启动、重复调用不生成重复数据；
- 进度查询不返回未投递 Match。

### Integration 测试

- 启动接口同步返回 S-08 完成后的运行状态；
- Application 查询只返回当前 Candidate 的记录；
- Application 包含匹配得分和推荐理由；
- 所有岗位无投递时返回统一空结果语义。

## 9. Implement / Verify 记录

- [x] 本文档和 S-08 Slice Spec 已锁定；
- [x] Integration Contract 和 Scenario 已锁定；
- [x] Match/Application/ProgressEvent 字段、索引和迁移已实现；
- [x] v0.1 参数和算法单测已实现；
- [x] 前端查询字段、得分/理由和空状态已同步；
- [x] 固定 `resume_01.pdf` 的解析回归已通过：`CandidateProfile.skills` 非空，工作/项目 `highlights` 已进入匹配输入快照；
- [x] 新运行已完成 7 个岗位的 Match 评估，2 个北京岗位被硬过滤，5 个岗位创建 Application；历史“2 个匹配”因无可比历史输入快照未作为算法参数调整依据；
- [x] S-07 同步编排、Application 查询 API 和幂等检查已实现；
- [x] 后端非 acceptance 回归、前端类型检查与测试、`git diff --check` 已通过；
- [x] 真实 API/数据库/前端闭环演示已通过；开发者复测已覆盖此前问题，`IS-S08-01` 已标记为 `integration_delivered`。
- [x] `APPLICATION-CONVERSATION@0.1` 已完成 S-08 → S10 前后端联调复验：Application 创建后唯一 Conversation 可被 HR 会话列表读取，首次消息为空且不写欢迎消息。

## 10. Close 结论

- S-08 的真实前后端闭环复测通过；此前记录的问题均已整改并通过开发者验收；
- `IS-S08-01` 已完成 Integration Verify 并标记为 `integration_delivered`；
- S-08 交付完成，后续投递状态推进仍归属 S-09。
- `APPLICATION-CONVERSATION@0.1` 已完成跨 Slice Handoff Verify，交付给 S10 消费。
