# 数据库设计

> 本文档用表格记录当前 Alembic 迁移链、已实现表和已通过 Slice Design 确认但尚未迁移的结构。
>
> 标记：`implemented` = 当前代码/迁移已落地；`planned` = Slice 已确认、待 Alembic 实现；`not confirmed` = 不提前设计。

## 1. 迁移链

| Revision | 状态 | 内容 |
| --- | --- | --- |
| `20260723_0001` | `implemented` | 空基线 |
| `20260725_0002` | `implemented` | `users`、`candidates` 认证与身份结构 |
| `20260727_0003` | `implemented` | 文件对象、简历、画像、附加资料、异步任务及枚举 |
| `20260815_0010` | `implemented` | S-04 工作年限改为带单位的确定性派生值 |
| `20260727_0004` | `implemented` | Dispatcher/Worker 投递与执行租约字段 |
| `20260813_0006` | `implemented` | HR-owned `jobs`、岗位文件关联和 `job_jd_parse` 任务枚举值 |
| `20260815_0007` | `implemented` | S-03 快照表、任务代数和脱敏失败语义字段 |
| `20260815_0008` | `implemented` | S-03 语义失败与旧解析失败码 CHECK 约束兼容；Dispatcher/Worker 超时失败字段边界 |
| `20260816_0011` | `implemented` | S-06 `job_goals` 当前求职目标、Candidate 唯一约束和字段 CHECK 约束 |
| `20260817_0012` | `implemented` | AgentRunContext 运行上下文、当前目标/简历/画像绑定、状态和幂等唯一约束 |
| `20260817_0013` | `implemented` | Match、Application、ProgressEvent、算法版本、评分快照和 `run_id + job_id` 幂等约束 |

## 2. 已实现表

| 表 | 主键/归属 | 关键字段 | 约束/索引 |
| --- | --- | --- | --- |
| `users` | `id` | `username`、`password_hash` | `username` 唯一；不保存密码原值 |
| `candidates` | `id`；`user_id → users` | `user_id` | `user_id` 唯一，一对一 |
| `hr_profiles` | `id`；`user_id → users` | `user_id` | `user_id` 唯一，一对一 |
| `user_roles` | `id`；`user_id → users` | 角色关联 | 服务端复核角色归属 |
| `stored_file_objects` | `id` | `storage_key`、`content_sha256`、状态 | `storage_key`、`content_sha256` 唯一；内部定位不进入 API |
| `resumes` | `id`；`candidate_id → candidates` | 文件引用、解析状态、失败分类 | 只接受 `ready` 文件对象；同一 Candidate 可有多条记录，内容重复上传复用已有记录 |
| `candidate_profiles` | `id`；`resume_id → resumes` | 结构化画像 | `resume_id` 唯一；`years_of_experience` 为 `unknown/x个月/x年` |
| `candidate_documents` | `id`；`candidate_id → candidates`；`stored_file_object_id → stored_file_objects` | `document_type` 固定为 `other`、`document_name`、`file_type`、文件引用和上传幂等键 | 仅保存成功资料；不进入解析任务；失败文件不落库 |
| `async_task_runs` | `id`；按 `resource_type/resource_id` 关联业务资源 | 任务类型、版本、幂等键、租约、终态 | `idempotency_key`、任务标识按当前迁移约束 |
| `parsed_job_description_snapshots` | `id`；`job_id → jobs` | `schema_version`、`fields`、`raw_sections`、创建时间 | `job_id` 唯一；成功快照才创建；`fields` 和 `raw_sections` 使用 JSONB；`implemented` |
| `job_goals` | `id`；`candidate_id → candidates` | `offer_target`、`title`、`filters`、`status`、时间字段 | `candidate_id` 唯一；Offer 数量 1–10；状态为 `active/achieved/abandoned`；不含 Resume 外键；`implemented` |
| `agent_run_contexts` | `id`；`candidate_id → candidates`；`job_goal_id → job_goals`；`resume_id → resumes`；`candidate_profile_id → candidate_profiles` | 目标快照、简历/画像绑定、`status`、结束原因、启动/结束时间 | `UNIQUE(candidate_id, job_goal_id)`；Candidate 归属；`running/finished`；`implemented` |

## 3. S-02 岗位表设计

### 3.1 表与字段

| 表 | 字段 | 类型/约束方向 | 说明 | 状态 |
| --- | --- | --- | --- | --- |
| `jobs` | `id` | UUID，主键 | 岗位资源标识 | `implemented` |
| `jobs` | `hr_profile_id` | UUID，非空，外键 → `hr_profiles.id` | 岗位所有者 | `implemented` |
| `jobs` | `stored_file_object_id` | UUID，非空，外键 → `stored_file_objects.id` | 唯一 JD 文件关联 | `implemented` |
| `jobs` | `created_at` | `TIMESTAMPTZ`，非空 | 创建时间 | `implemented` |

Job 不新增以下字段：

| 不保存字段 | 事实来源 |
| --- | --- |
| `title`、`company_name`、`location`、`salary_range` | S-03 结构化 JD 快照 |
| `summary`、职责、任职要求 | S-03 结构化 JD 快照 |
| JD 解析状态 | S-03 任务/资源状态 |
| JD 版本号 | 当前版本不建立版本模型 |

### 3.2 关系

| 主表 | 关系 | 从表 | 说明 |
| --- | --- | --- | --- |
| `hr_profiles` | 1 : N | `jobs` | 一个 HR 可拥有多个独立岗位 |
| `jobs` | 1 : 1 | `stored_file_objects` | 每个 Job 绑定一个 JD 文件 |
| `jobs` | 1 : 0..1 | `parsed_job_description_snapshots` | 每个 Job 至多一个当前有效快照；成功解析且核心字段完整后创建 |
| `jobs` | 1 : 1 有效任务 | `async_task_runs` | 新 Job 在上传事务内创建/复用 queued 任务；任务字段由 S-03 锁定 |

JD 输入资源不单独建表，由 `jobs.stored_file_object_id` 表达。

### 3.3 约束与索引方向

| 类型 | 建议定义 | 目的 | 状态 |
| --- | --- | --- | --- |
| 外键 | `jobs.hr_profile_id → hr_profiles.id` | 保证岗位归属主体存在 | `implemented` |
| 外键 | `jobs.stored_file_object_id → stored_file_objects.id` | 保证 JD 文件关联存在 | `implemented` |
| 非空 | `hr_profile_id`、`stored_file_object_id`、`created_at` | Job 最小完整性 | `implemented` |
| 唯一约束 | `UNIQUE(hr_profile_id, stored_file_object_id)`（未删除记录） | 同一 HR 顺序重复上传复用已有 Job | `implemented` |
| 查询索引 | `INDEX(hr_profile_id, created_at)` | 查询当前 HR 岗位列表 | `implemented` |
| 内容去重 | 使用关联 `StoredFileObject.content_sha256` 做当前 HR 的顺序重复判断 | 不在 Job 重复保存摘要 | `implemented` |

当前 Demo 不定义：跨 HR 相同内容的业务复用约束、并发重复上传竞态约束和岗位版本约束。

## 4. 枚举与状态

| 枚举/状态 | 当前值 | 归属 | 状态 |
| --- | --- | --- | --- |
| `stored_file_object_status_enum` | `writing`、`ready`、`deleting` | StoredFileObject | `implemented` |
| `parse_status_enum` | `processing`、`succeeded`、`failed` | Resume 和岗位 JD 解析 | `implemented`；岗位匹配资格由 S-03 结果单独表达 |
| `parse_failure_code_enum` | `unsupported_file`、`file_unreadable`、`storage_unavailable`、`parser_timeout`、`schema_validation_failed`、`internal_error` | 解析任务/资源 | `implemented`；S-03 使用独立 `failure_semantics` 表达临时技术失败、输入不可用和核心字段缺失，核心字段缺失不得映射为 `schema_validation_failed` |
| `async_task_type_enum` | `resume_parse`、`job_jd_parse` | AsyncTaskRun | `implemented`；`job_jd_parse` 由 S-02 revision 落实 |
| `async_task_resource_type_enum` | `resume`、`job` | AsyncTaskRun | `implemented`；`job` 由 S-02 revision 落实 |
| `async_task_run_status_enum` | `queued`、`running`、`succeeded`、`failed` | AsyncTaskRun | `implemented` |
| AgentRunContext 状态 | `running`、`finished` | AgentRunContext | `implemented`；S-08 可写入 `finished/no_match` |
| Job 业务状态 | 暂不新增通用 `status` | Job | `planned`；删除资格由 S-11/S-08 业务规则判断 |

## 5. 事务与数据边界

| 场景 | 原子范围/规则 |
| --- | --- |
| S-02 新 Job 上传 | 文件对象元数据、Job、文件关联和 queued S-03 任务交接记录在同一 PostgreSQL 事务内提交 |
| S-02 重复上传 | 查询并返回当前 HR 已有 Job；不新建 Job，不新建解析任务 |
| 批量上传 | 每个文件独立处理，允许部分成功；批次不要求全成全败 |
| 文件/事务失败 | 不留下可供 S-03 消费的半成品 Job 输入；未引用临时对象按对象存储清理规则处理 |
| S-03 解析 | S-03 独立更新解析任务；成功且五项核心字段有效时创建结构化快照；核心字段缺失、临时技术失败重试耗尽或输入不可用不形成可供 S-08 使用的快照；不回滚已提交的 S-02 Job |
| Job 删除 | 匹配开始前可删除；匹配已发起后不可删除；具体软删除/对象清理由 S-11 设计 |
| 内部定位 | 生产任务只携带资源标识；纯内部验证 API 可短暂接收受控 `local_path`，但路径不进入任务持久化、普通响应、日志或追踪 |
| S-07 启动 | 目标快照、当前简历和画像绑定、运行状态和唯一约束在同一事务内提交；不检查 JD，不创建匹配/投递记录 |

## 6. 后续 Slice 表设计

| 表/对象 | 原因 |
| --- | --- |
| `Match` | S-08 独立保存岗位筛选结果、算法版本、已脱敏输入快照、三维分数、总分、状态、推荐理由和原因码；`UNIQUE(run_id, job_id)`；`slice-confirmed` |
| `Application` | S-08 为通过投递筛选的 Match 创建；绑定 Candidate、Job、AgentRun 和 Match，初始状态为 `submitted`；`UNIQUE(run_id, job_id)`；`slice-confirmed` |
| `ProgressEvent` | S-08 创建 Application 时写入 `application_created` 初始事件；后续状态事件由 S-09/S-10 使用；`slice-confirmed` |
| `Conversation`、`Message` | 由沟通 Slice 负责 |

### 6.1 S-08 计划表

| 表 | 核心字段 | 约束/索引 | 业务用途 |
| --- | --- | --- | --- |
| `matches` | `run_id`、`candidate_id`、`job_id`、`algorithm_version`、`input_snapshot`、状态、三维得分、总分、推荐理由、原因码、时间字段 | 外键归属；`UNIQUE(run_id, job_id)`；按 Candidate/Run/Job 查询 | 独立保存每个岗位的筛选结果 |
| `applications` | `run_id`、`match_id`、`candidate_id`、`job_id`、状态、投递时间、时间字段 | `match_id` 唯一；`UNIQUE(run_id, job_id)`；状态由合法迁移控制 | 保存通过筛选的系统内投递记录 |
| `progress_events` | Application、事件类型、前状态、后状态、操作者主体、时间和脱敏载荷 | 按 Application/时间查询；不得保存原文和凭证 | 保存 Application 创建及后续状态事件 |

S-08 只保存已解析业务语义快照，不保存 JD/简历原文、文件路径、联系方式或模型原始响应。具体类型、枚举和索引由 `20260817_0013` 和 S-08 Technical Design 实现。

## 7. 变更规则

| 变化 | 处理 |
| --- | --- |
| 新增表、字段、约束、索引 | 先通过对应 Slice Readiness Check，再新增 Alembic revision |
| 修改已执行迁移 | 禁止原地修改，新增 revision |
| Job 字段或关系变化 | 回退 S-02 Slice Design，并同步领域模型、业务规则和本文档 |
