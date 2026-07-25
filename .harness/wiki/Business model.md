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
|   file_url | String  | 文件存储地址 | 
|   file_type | String | 文件类型 | 
|   parse_status | Enum  |  文件解析状态  | 
|   parse_error | Text  | 文件解析失败原因 | 

### Candidate Profile（求职者画像）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  profile_id  | UUID | 求职者画像唯一标识 | 
|  resume_id| UUID | 画像来源的简历唯一标识 | 
|  target_job_titles| String |目标岗位名称 | 
|  skills| JSON/List | 技术技能及熟练程度 | 
|  work_experience_summary |JSON| 工作经历摘要 | 
|  project_experience_summary |JSON| 项目经历摘要 | 
|  years_of_experience |INT| 工作年限 | 

### Candidate Document（求职者附加资料）

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  document_id  | UUID | 资料唯一标识 | 
|  candidate_id| UUID | 所属求职者 | 
|  document_type| Enum | 资料类型 | 
|  document_name | String | 资料名称 | 
|  file_url | String | 资料存储地址 | 
|  file_type | String  | 文件类型 | 

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
|  document_type | Enum | 附件资料类型 | 
|  document_name | String | 附件名称 | 
|  file_url | String | 文件存储地址 | 
|  file_type | String | 文件类型 | 
|  parse_status | Enum | 文件解析状态 | 
|  parse_error | Text | 文件解析失败原因 | 

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
 	求职者资料仅存放 `document_type` 定义的非简历附加材料，用于补充信息和 Agent 上下文。
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

### 资料处理流程

```读取文件 → 文档解析 → 信息抽取 → 数据结构化 → Embedding生成 → 索引建立 → 更新处理状态```

1. 系统根据资料记录读取对应文件
2. 系统进行文档解析
3. 系统进行信息抽取
4. 系统生成结构化业务数据
5. 系统生成Embedding向量
6. 系统建立向量索引
7. 更新资料处理状态

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
