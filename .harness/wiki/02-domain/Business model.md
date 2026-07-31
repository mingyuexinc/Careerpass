# 业务模型

## 实体说明

### User（用户）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -|
|  user_id  | UUID | 用户ID | 
|  password_hash | String | 密码哈希 | 
|  created_at | DateTime | 创建时间 | 

### Authentication Session（认证会话）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -|
| session_id | UUID | 认证会话唯一标识 |
| user_id | UUID | 所属用户账号；一个用户可拥有多个设备或客户端会话 |
| token_hash | String | Refresh Token 的 HMAC-SHA-256 摘要；仅保存摘要，不保存 Token 明文 |
| token_family_id | UUID | 同一次登录及后续轮换产生的 Token 家族标识，用于重放检测后的整链撤销 |
| parent_session_id | UUID | 上一次轮换产生本会话的认证会话；首次登录时为空 |
| issued_at | DateTime | Refresh Token 签发时间 |
| expires_at | DateTime | Refresh Token 到期时间 |
| revoked_at | DateTime | 会话撤销时间；为空表示尚未撤销 |
| revoked_reason | String | 撤销原因，如 `logout`、`rotated`、`replay_detected`、`password_changed` |
| last_used_at | DateTime | 最近一次使用 Refresh Token 刷新 Access Token 的时间 |
| created_at | DateTime | 记录创建时间 |

认证会话是用户的一对多从属实体，不关联 Candidate。Access Token 为短期无状态凭证，不作为业务实体持久化；Refresh Token 仅通过认证会话进行轮换、撤销和审计。

### Candidate（求职者）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  candidate_id  | UUID | 求职者ID | 
|   user_id | UUID | 关联用户账号 | 

### Resume（简历）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  resume_id  | UUID | 简历ID | 
|   candidate_id | UUID | 所属求职者 | 
|   stored_file_object_id | UUID | 内部文件对象引用 |
|   file_type | String | 文件类型 | 
|   parse_status | Enum  |  文件解析状态  | 

### Stored File Object（内部文件对象）

| Field | Type | Description |
| --- | --- | --- |
| object_id | UUID | 内部对象唯一标识 |
| storage_key | String | 随机生成的不透明定位键，不对客户端暴露 |
| content_sha256 | String | 服务端内容摘要；全局唯一去重键 |
| detected_mime_type | String | 服务端检测 MIME 类型 |
| file_size_bytes | Integer | 服务端校验字节数，最大 10,000,000 |
| status | Enum | `writing`、`ready`、`deleting`；仅对象存储内部使用 |

内部对象目录不是通用文件中心。简历和候选人附加资料只引用 `object_id`；清理任务必须在事务内确认无任何资源引用后才可删除底层文件。

### Candidate Profile（求职者画像）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  profile_id  | UUID | 求职者画像唯一标识 | 
|  resume_id| UUID | 画像来源的简历唯一标识 | 
|  target_job_titles| List[String] |从简历提取的目标岗位名称列表（至少一个） |
|  skills| JSON/List | 技术技能及熟练程度 | 
|  work_experience_summary |JSON| 工作经历摘要 | 
|  project_experience_summary |JSON| 项目经历摘要 | 
|  years_of_experience |INT| 工作年限 | 

候选人画像是已成功解析简历的确定性派生结果：简历结构化结果与画像在同一解析工作流中校验并原子持久化。`resumes.parse_status = succeeded` 的必要条件包括对应画像已成功写入，因此“画像成功”不是独立终态；画像生成、校验或写入失败均使简历以 `parse_status = failed` 终态失败。`candidate_profiles` 是 MVP 下游模块读取简历结构化事实的唯一来源，字段必须覆盖岗位匹配、投递和 AI 沟通在 MVP 中实际需要的简历信息；`resumes` 不保存重复的 `parse_data`。`target_job_titles` 是从简历提取的目标职位事实，按“至少一个非空字符串”的列表持久化；即使只有一个目标职位，也使用单元素列表，不使用标量字符串。它不是系统基于技能、经历或市场信息生成的推荐结果。每份简历最多对应一份有效画像，不设置独立的画像处理中或失败状态。后续下游确需新增简历字段时，须先扩展画像 Schema，并使用已保存的原始简历文件按新的解析任务版本重新解析和原子更新画像；不得以临时 JSON 或未校验的历史解析输出绕过该流程。

### Async Task Run（异步任务运行）

异步任务运行用于持久化任务与业务资源的关联、幂等与脱敏审计事实。Celery 负责重试次数、退避/延迟、下次执行时间、超时和 Worker 运行时元数据；本实体不重复保存这些执行策略。

| Field | Type | Description |
|- - - - |- - - - -|
| task_run_id | UUID | 异步任务运行唯一标识 |
| task_type | Enum | 任务类型；MVP 首批包括 `resume_parse`，岗位匹配任务后续复用该模型 |
| resource_type | Enum/String | 被处理资源类型，例如 `resume`；用于定位业务资源和其归属链 |
| resource_id | UUID | 被处理资源的唯一标识 |
| celery_task_id | String | Celery 已接受投递后的任务标识；`queued` 且为空表示仍待可靠投递；不作为资源归属或幂等判断依据 |
| idempotency_key | String | 确定性幂等标识，固定格式为 `{task_type}:{resource_id}:{task_version}`；不得使用文件名、文件内容或随机值 |
| status | Enum | 当前运行状态：`queued`、`running`、`succeeded`、`failed` |
| task_version | String | MVP 固定为内部常量 `v1`，仅用于既有幂等键；不提供版本管理能力 |
| failure_code | parse_failure_code Enum | 解析任务终态失败的脱敏分类；成功时为空；是解析资源失败原因的唯一权威来源 |
| created_at | DateTime | 任务运行记录创建时间 |
| finished_at | DateTime | 终态完成时间；未终态时为空 |

**实体关系与约束：**

- 每个异步资源在固定的 `task_type + task_version(v1)` 下只允许关联一条 `Async Task Run`；用户重新上传会创建新资源，每次运行仅处理一个确定的资源。MVP 不处理解析器升级或新版本重跑。
- `Async Task Run` 的候选人归属不冗余保存，必须由 `resource_type + resource_id` 指向的资源归属链推导并在 Repository 中校验。非资源所有者不得通过 `task_run_id` 查询、重试或消费任务。
- 同一 `resource_type`、`resource_id`、`task_type`、`task_version` 和确定性 `idempotency_key` 全量唯一；Celery 重试、重复回调或重复投递必须复用同一任务运行，不能新建记录或重复产生业务结果。
- 对简历异步解析，`AsyncTaskRun.failure_code` 是失败原因的唯一权威来源，并共用 `parse_failure_code` 枚举；资源表只保存 `parse_status`，不保存自由文本 `parse_error`。查询失败资源时，Repository 必须按资源类型、资源 ID 与解析任务类型定位其终态任务运行并返回允许暴露的脱敏分类。不得保存简历原文、文件地址、联系方式、模型原始响应、Token 或堆栈。
- `max_retries`、退避/延迟、下次重试时间、超时和每次执行的运行时详情由 Celery 任务定义、Worker 与 Result Backend 管理；它们不是 MVP 业务模型字段。需要排查时，以 `celery_task_id` 关联运行时信息。

**可靠入队约定：**

1. 上传服务在同一数据库事务内创建资源（`parse_status = processing`）和 `AsyncTaskRun`（`status = queued`、`celery_task_id = NULL`）；提交前不得直接发送 Celery 消息。
2. Dispatcher 为独立、单实例的内部常驻进程，不由 Celery Beat 驱动；它仅通过 Repository 以数据库行锁领取有限批次的 `status = queued AND celery_task_id IS NULL` 记录，以任务运行 ID 作为确定性的 Celery 任务 ID 投递已注册任务。Broker 接受后回填 `celery_task_id`。Broker 调用失败时保持该记录可再次领取，不能删除资源或将其误标为 `failed`。
3. 若 Broker 已接受消息但 Dispatcher 在回填前中断，后续投递可重复发送同一任务运行 ID；Worker 必须原子取得 `queued → running` 的唯一执行权，重复消息安全确认但不得重复写入业务结果。该机制提供至少一次投递与业务结果幂等，不承诺恰好一次消息投递。

**资源状态与任务状态的区别：**

```text
Resume.parse_status
  = 资源的最终解析结果是否可供下游业务使用

AsyncTaskRun.status
  = 某一次后台执行是否排队、运行、成功或终态失败
```

例如解析任务遇到可重试超时时，Celery 依据任务配置重新调度执行，`AsyncTaskRun` 保持或回到 `queued`，而简历的 `parse_status` 继续保持 `processing`。只有任务成功完成结构化校验并原子写入结果后，资源才变为 `succeeded`；Celery 重试耗尽或发生确定性失败后，资源才变为 `failed`。

### Candidate Document（求职者附加资料）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  document_id  | UUID | 资料唯一标识 | 
|  candidate_id| UUID | 所属求职者 | 
|  document_type| Enum | 资料类型 | 
|  document_name | String | 资料名称 | 
|  stored_file_object_id | UUID | 内部文件对象引用 |
|  file_type | String  | 文件类型 | 

候选人附加资料是原始文件附件，不参与解析、画像或匹配输入；其文件格式只影响上传校验，不改变该业务边界。候选人明确选择后，它可作为系统内沟通消息的附件引用；MVP 中 Agent 仅可使用最小附件元数据，资料正文不自动进入 Agent/LLM 输入。

### Job Goal（求职目标）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  goal_id | UUID | 求职目标唯一标识 | 
|  candidate_id| UUID | 所属求职者 | 
|  target_offer_count| Integer | 目标 Offer 数量 | 
|  current_offer_count | Integer | 当前已获得 Offer 数量 | 
|  Status | Enum | 目标状态 | 
|  filter_conditions | JSON | 岗位过滤条件（内嵌值对象） | 

### Filter Conditions（岗位过滤条件）
- 备注：作为 `Job Goal.filter_conditions` 的内嵌值对象存储，不单独建表。
- `include`、`exclude` 及其所有子字段均为可选；未提供的字段不参与过滤。
- 示例：

```json
{
  "include": {
    "job_nature": ["fulltime"]
  },
  "exclude": {
    "locations": ["北京"],
    "employment_type": ["outsource"],
    "interview_mode": ["offline"]
  }
}
```

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  include.job_nature | List[String] | 可选；包含的岗位性质 | 
|  exclude.locations | List[String] | 可选；排除的岗位地点 | 
|  exclude.employment_type | List[String] | 可选；排除的雇佣模式 | 
|  exclude.interview_mode | List[String] | 可选；排除的面试模式 | 


### Job （岗位）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  job_id | UUID | 岗位唯一标识 | 
|  job_title | String | 岗位名称 | 
|  company_name | String | 公司名称 | 
|  location | String | 工作地点 |
|  salary_range | String | 薪资范围 |
|  job_nature | String | 岗位性质 |
|  employment_type | String | 雇佣模式 |
|  interview_mode | String | 面试形式 |

- 说明：企业信息在当前版本扁平化存储于 `Job.company_name`，不定义独立的 `Company` 实体或企业表。

### Job Description（岗位JD）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  job_description_id | UUID | JD唯一标识 | 
|  job_id | UUID | 所属岗位 | 
|  raw_content | Text | 原始JD文本 | 
|  responsibilities | List[String] | 岗位职责 | 
|  job_requirements | List[Object] | 任职要求 | 
|  parse_data | JSON  |  完整结构化解析结果  | 
|  parse_status | Enum  |  解析状态  | 

岗位与 JD 是系统受控启动导入的共享资源，不归属于候选人，也不提供候选人侧创建、更新或删除。导入命令只读取固定专属目录中的 Markdown 文件，单文件上限为 1 MB；文件名仅用于受控归档，不承载岗位业务含义。岗位元数据、JD 正文及其结构化结果均由文件正文提供，并通过第 5 步裁定的校验后写入。

MVP 不更新既有 JD；新文件只会新增岗位资源。第 4 步只建立输入与归档边界；第 5 步解析失败时不持久化 `Job` 或 `JobDescription`，原文件移入受控失败归档区；候选人只能查询第 5 步成功写入且 `parse_status = succeeded` 的岗位/JD 快照。原始导入文件在成功后移入受控成功归档区，业务表持久化 `raw_content`，但 API 不返回内部路径或文件名。

### Match Run（岗位匹配批次）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  match_run_id | UUID | 匹配批次唯一标识 | 
|  goal_id | UUID | 关联求职目标 | 
|  result_count | Integer | 本次匹配批次生成的结果数量 | 
|  status | Enum  |  执行状态  | 
|  created_at | DateTime  |  创建时间  | 


### Match Result（匹配结果）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  match_id | UUID | 匹配结果唯一标识 | 
|  match_run_id | UUID | 匹配批次唯一标识 | 
|  profile_id | UUID | 使用的求职者画像版本 | 
|  job_id | UUID | 岗位标识 | 
|  recall_score | Decimal | 召回相似度得分 | 
|  experience_match_score| Decimal  |  经验匹配分  | 
|  skill_match_score | Decimal  |  技能匹配分  | 
|  salary_match_score | Decimal  |  薪资匹配分  | 
|  final_match_score | Decimal  |  综合匹配分  | 
|  algorithm_version | VARCHAR  |  本次匹配使用的算法或规则版本  | 

匹配结果仅在全部评分、推荐解释和 `algorithm_version` 已生成后持久化；匹配批次失败时不产生不完整的匹配结果。

### Application（投递记录）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  application_id | UUID | 求职申请唯一标识 | 
|  job_id | UUID | 投递岗位标识 | 
|  resume_id | UUID | 投递时使用的简历 | 
|  match_result_id | UUID | 对应的岗位匹配结果 | 
|  goal_id | UUID  |  所属求职目标  | 
|  applied_at | DateTime  |  投递时间  | 
|  status | Enum  | 投递状态 | 

### Conversation（沟通会话）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  conversation_id | UUID | 会话唯一标识 | 
|  application_id| UUID | 关联的求职申请 | 
|  last_message_at| DateTime | 最后一条消息时间  | 
|  summary| Text  |  会话滚动摘要  | 
|  created_at | DateTime  |  会话创建时间  | 

### Message（沟通消息）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  message_id | UUID | 消息唯一标识 | 
|  conversation_id | UUID | 所属会话 | 
|  role | Enum | 消息发送方角色 | 
|  content| Text | 消息正文  | 
|  attachment_ids | List[UUID]  |  附件资料标识  | 
|  intent | Enum  |  消息意图,可为空  | 
|  created_at| DateTime | 消息创建或发送时间  | 

### Attachment（消息附件）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  attachment_id | UUID | 附件唯一标识 | 
|  message_id | UUID | 所属消息；附件的归属锚点 | 
|  candidate_document_id | UUID | 被消息引用的候选人附加资料 |

消息附件是候选人附加资料被发送到某条会话消息中的引用记录，不复制文件或资料正文。同一份由候选人明确授权的资料可被多个消息引用；消息所属候选人与资料所属候选人必须一致。

### Progress Event（进度事件）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  event_id | UUID | 事件唯一标识 | 
|  application_id | UUID | 关联申请 | 
|  from_stage| Enum | 投递进度变更前状态 | 
|  to_stage | Enum  |  投递进度变更后状态  | 
|  created_at| DateTime | 系统记录时间  | 
- 备注1：实体边界说明

``````txt
（1）简历与求职者资料的边界：
	`Resume` 与 `Candidate Document` 是两个独立资源，不存在包含关系。
 	简历只存放正式求职简历，承担解析、画像生成、岗位匹配和投递依据等职责。
 	求职者资料仅存放 `document_type` 定义的非简历附加材料；候选人明确选择后可作为系统内沟通消息的附件引用，不作为默认 Agent 上下文。
 	不允许通过 `Candidate Document` 创建或替代 `Resume`。
``````



## 核心业务流程

### 资料上传流程

```上传资料 → 文件校验 → 文件存储 → 创建资料记录 → 异步处理  ```

1. 用户（求职者/HR）上传对应的求职/招聘资料
2. 系统对文件格式&完整性进行校验
3. 系统将文件进行存储（对象存储/本地存储）
4. 系统创建资料记录（文件元数据）
5. 系统触发异步处理任务

### 简历处理流程

```创建任务运行记录 → 读取简历 → 简历解析 → 信息抽取 → 数据结构化与校验 → 原子更新资源状态 → 触发允许的下游任务```

1. 系统在同一事务内为资料资源创建带幂等键的 `Async Task Run`，并将任务置于 `queued`、`celery_task_id = NULL`。
2. Dispatcher 在事务提交后可靠投递已注册 Celery 任务，并在 Broker 接受后回填 `celery_task_id`。
3. Worker 原子取得唯一有效执行权后读取被授权文件，并将任务置于 `running`。
4. 系统进行简历解析、信息抽取和结构化校验。
5. 校验成功时，系统原子持久化完整业务结果，将任务和资源分别更新为 `succeeded`。
6. 发生临时故障时，Celery 按任务配置的有限重试策略重新排队；资源保持 `processing`。
7. 重试耗尽或发生确定性错误时，系统将任务和资源更新为 `failed`，仅记录脱敏失败分类。
7. 简历解析成功时，确定性画像已与解析结果原子写入；Embedding 或索引等后续动作仅在匹配模块实际启用相应能力时由显式任务触发，不是资料处理的固定步骤。

### 求职目标创建流程

```简历分析 → 生成目标建议 → 用户选择/补充目标信息 → 目标完整性校验 → 创建求职目标 → 进入执行流程```

1. 系统根据求职者上传简历资料生成目标建议
2. 用户补充求职目标信息并完成确认
3. 系统创建求职目标
4. 求职目标进入执行流程

### 岗位匹配流程

```读取求职目标 → 加载求职者资料 → 多路召回候选岗位 → 匹配评分与重排序 → 生成Top-N推荐岗位```
1. 系统读取当前创建生效的求职目标
2. 系统加载求职者的结构化资料和简历信息
3. 根据岗位匹配算法多路召回候选岗位
4. 系统对候选岗位进行匹配评分和重排序
5. 系统生成 Top-N 推荐岗位，供后续投递流程使用

### 岗位投递流程

```岗位推荐结果 → 创建岗位申请记录 → 关联投递简历 → 更新求职状态&投递信息```
1. 系统读取当前轮次岗位匹配产生的推荐结果
2. 系统根据求职者和岗位创建Application记录
3. 系统为岗位申请关联本次实际使用的简历及其版本
4. 系统将岗位申请更新为已投递状态，并记录投递时间等信息

### AI求职沟通流程

```收到HR消息&主动触发沟通 → 识别关联岗位申请 → 加载会话历史与求职策略 → 分析沟通意图及待确认信息 → 检索资料或调用工具 → 生成回复或主动询问 → 记录沟通消息 → 提取并更新业务信息 → 执行求职策略校验 → 更新申请状态或后续动作```
1. 系统接收 HR 发送的消息或者触发主动沟通任务
2. 系统识别消息所属的岗位申请
3. 系统加载对应的会话历史、求职者资料、申请状态及当前求职目标
4. 系统识别当前沟通意图，检查用户关心的岗位过滤信息是否仍存在未知项
5. 系统根据沟通任务检索资料以及调用工具
6. 系统生成回复内容或者结合当前对话主动向HR提问
7. 系统保存求职者与 HR 的沟通消息，并维护当前会话上下文
8. 系统从 HR 消息中提取结构化业务信息
9. 系统将已经获取的岗位信息与用户设置的求职过滤条件进行比对，判断当前岗位是否仍符合求职策略
10. 系统根据校验结果，系统决定继续沟通或者终止后续推进

### 求职进度更新流程

```接收HR进度更新 → 更新岗位申请阶段 → 记录变更进度```
1. 系统接收HR对于求职状态的更新信息
2. 系统根据更新信息更新岗位申请阶段
3. 系统记录岗位求职记录变更进度信息
