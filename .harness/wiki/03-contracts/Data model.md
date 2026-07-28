





# 数据模型

## 通用审计时间字段约定

- `created_at` 仅在插入记录时由数据库默认值 `CURRENT_TIMESTAMP` 初始化，后续更新不得修改该字段。
- 所有声明 `updated_at` 的表，必须由 PostgreSQL `BEFORE UPDATE FOR EACH ROW` 触发器将其设置为 `CURRENT_TIMESTAMP`。
- 共用触发器函数命名为 `set_updated_at()`；各表触发器命名格式为 `trg_<table_name>_set_updated_at`。
- Repository、Service、Agent 不得手动设置或信任请求中传入的 `updated_at`；数据库触发器是该字段的最终约束。
- 当前适用表为用户表和求职者表。后续任何新增 `updated_at` 字段的表，均必须在同一数据库迁移中绑定该触发器。

## 关联资源归属与去冗余约定

- 匹配批次的候选人归属由 `job_goal_id → job_goal.candidate_id` 唯一确定；不保存冗余 `candidate_id`。写入时 Repository 必须原子校验 `resume_id` 也属于该候选人。
- 求职者画像的候选人归属由 `resume_id → resume.candidate_id` 唯一确定；不保存冗余 `candidate_id`。所有画像读取、创建和更新均须经该链路校验当前候选人。
- 匹配结果的候选人归属由 `match_run_id → job_goal_id → candidate_id` 确定；写入时 Repository 必须原子校验 `profile_id` 属于该候选人。
- 投递记录的候选人归属由 `goal_id → job_goal.candidate_id` 确定；不保存冗余 `candidate_id`。写入时 Repository 必须原子校验 `resume_id` 及可选的 `match_result_id` 均属于该候选人。
- 沟通会话的候选人归属由 `application_id → goal_id → candidate_id` 确定；不保存冗余 `candidate_id`。
- 所有读取、创建和更新均须通过上述归属链校验当前候选人，禁止仅凭资源 ID 访问或修改。

## 表结构定义

### 版本适用范围

| 标记 | 含义 |
| --- | --- |
| `MVP` | 当前 MVP 必须迁移并由实现使用的数据库对象。 |
| `Deferred` | 已完成设计但不属于当前 MVP 迁移或实现范围的后续数据库对象。 |

范围裁决以 `.harness/wiki/01-governance/MVP scope and development boundaries.md` 为最高依据。`Deferred` 对象可保留在数据模型中供后续阶段使用，但不得作为 MVP 的迁移前置条件。

### 用户表（`users`，`MVP`）

1. 表结构

| Column        | Type         | Nullable | Default           | Description |
| ------------- | ------------ | -------- | ----------------- | ----------- |
| id            | UUID         | NO       | gen_random_uuid() | 主键        |
| username      | VARCHAR(64)  | NO       | 无                | 用户名      |
| password_hash | VARCHAR(255) | NO       | 无                | 密码哈希    |
| created_at    | TIMESTAMPTZ  | NO       | CURRENT_TIMESTAMP | 创建时间    |
| updated_at    | TIMESTAMPTZ  | NO       | CURRENT_TIMESTAMP | 插入默认值由数据库提供；更新时由 `BEFORE UPDATE` 触发器维护 |

2. 外键约束

| Constraint Name | Local Column | Referenced Table | Referenced Column | On Delete | Description |
| --------------- | ------------ | ---------------- | ----------------- | --------- | ----------- |

3. 索引

| Name    | Columns | Type    |
| ------- | ------- | ------- |
| PRIMARY | id      | PRIMARY |
| uq_user_username | username | UNIQUE |

### 认证会话表（`auth_sessions`，`Deferred`）

1. 表结构

| Column            | Type         | Nullable | Default           | Description |
| ----------------- | ------------ | -------- | ----------------- | ----------- |
| id                | UUID         | NO       | gen_random_uuid() | 主键 |
| user_id           | UUID         | NO       | 无                | 所属用户 ID |
| token_hash        | CHAR(64)     | NO       | 无                | Refresh Token 的 HMAC-SHA-256 十六进制摘要；禁止保存 Token 明文 |
| token_family_id   | UUID         | NO       | 无                | 登录会话及其 Token 轮换链路标识 |
| parent_session_id | UUID         | YES      | NULL              | 上一次轮换产生本会话的认证会话 ID；首次登录为空 |
| issued_at         | TIMESTAMPTZ  | NO       | CURRENT_TIMESTAMP | Refresh Token 签发时间 |
| expires_at        | TIMESTAMPTZ  | NO       | 无                | Refresh Token 到期时间 |
| revoked_at        | TIMESTAMPTZ  | YES      | NULL              | 会话撤销时间 |
| revoked_reason    | VARCHAR(32)  | YES      | NULL              | 撤销原因：`logout`、`rotated`、`replay_detected`、`password_changed` 等 |
| last_used_at      | TIMESTAMPTZ  | YES      | NULL              | 最近一次成功刷新时间 |
| created_at        | TIMESTAMPTZ  | NO       | CURRENT_TIMESTAMP | 记录创建时间 |

2. 外键约束

| Constraint Name             | Local Column      | Referenced Table | Referenced Column | On Delete | Description |
| --------------------------- | ----------------- | ---------------- | ----------------- | --------- | ----------- |
| fk_auth_session_user        | user_id           | 用户表           | id                | CASCADE   | 认证会话所属用户；删除用户时清理其会话 |
| fk_auth_session_parent      | parent_session_id | 认证会话表       | id                | RESTRICT  | 保留 Token 轮换链路，禁止删除仍被后继会话引用的会话 |

3. 检查约束

| Constraint Name | Rule | Description |
| --------------- | ---- | ----------- |
| ck_auth_session_expiry | `expires_at > issued_at` | 会话到期时间必须晚于签发时间 |
| ck_auth_session_revocation | `revoked_at IS NULL OR revoked_at >= issued_at` | 撤销时间不得早于签发时间 |

4. 索引

| Name | Columns | Type |
| ---- | ------- | ---- |
| PRIMARY | id | PRIMARY |
| uq_auth_session_token_hash | token_hash | UNIQUE |
| idx_auth_session_user_active | user_id, expires_at | PARTIAL INDEX (`revoked_at IS NULL`) |
| idx_auth_session_family | token_family_id | INDEX |
| idx_auth_session_parent | parent_session_id | INDEX |

`auth_sessions` 仅保存 Refresh Token 的 HMAC 摘要。Refresh Token 刷新时，旧会话必须标记为已撤销且 `revoked_reason = rotated`，然后创建继承相同 `token_family_id` 的新会话；检测到已轮换 Token 被重放时，必须撤销该 `token_family_id` 下全部未撤销会话。

### 求职者表（`candidates`，`MVP`）

1. 表结构

| Column     | Type        | Nullable | Default           | Description |
| ---------- | ----------- | -------- | ----------------- | ----------- |
| id         | UUID        | NO       | gen_random_uuid() | 主键        |
| user_id    | UUID        | NO       | 无                | 用户ID      |
| name       | VARCHAR(64) | YES      | NULL              | 姓名        |
| created_at | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 创建时间    |
| updated_at | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 插入默认值由数据库提供；更新时由 `BEFORE UPDATE` 触发器维护 |

2. 外键约束

| Constraint Name    | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| ------------------ | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_candidate_user | user_id      | 用户表           | id                | RESTRICT  | 求职者关联的用户账户 |

3. 索引

| Name    | Columns | Type    |
| ------- | ------- | ------- |
| PRIMARY | id      | PRIMARY |
| uq_candidate_user_id | user_id | UNIQUE |

`uq_candidate_user_id` 约束 `users` 与 `candidates` 为一对一关系：每个用户仅能关联一个候选人；注册流程必须在同一事务中创建该候选人记录。

### 内部文件对象表（`stored_file_objects`，`MVP`）

内部文件对象目录；`resumes` 与 `candidate_documents` 通过外键引用该表。对象存储的去重、受控读取和清理机制以 [对象存储技术方案](../04-technical-solutions/Object%20storage%20technical%20design.md) 为准。

| Column | Type | Nullable | Default | Description |
| --- | --- | --- | --- | --- |
| id | UUID | NO | gen_random_uuid() | 内部对象主键 |
| storage_key | VARCHAR(512) | NO | 无 | 随机生成的不透明对象定位键；不得返回客户端 |
| content_sha256 | CHAR(64) | NO | 无 | 服务端计算的内容摘要；底层对象去重键 |
| detected_mime_type | VARCHAR(255) | NO | 无 | 服务端检测到的 MIME 类型 |
| file_size_bytes | BIGINT | NO | 无 | 服务端校验后的文件字节数，最大 10,000,000 |
| status | stored_file_object_status_enum | NO | writing | 内部写入/就绪/删除中状态，不是业务资源状态 |
| created_at | TIMESTAMPTZ | NO | CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMPTZ | NO | CURRENT_TIMESTAMP | 最近状态更新时间 |

约束与索引：`storage_key`、`content_sha256` 均唯一；`file_size_bytes > 0 AND file_size_bytes <= 10000000`。

### 简历表（`resumes`，`MVP`）

1. 表结构

| Column       | Type              | Nullable | Default           | Description  |
| ------------ | ----------------- | -------- | ----------------- | ------------ |
| id           | UUID              | NO       | gen_random_uuid() | 主键         |
| candidate_id | UUID              | NO       | 无                | 求职者ID     |
| upload_idempotency_key | UUID       | YES      | NULL              | 客户端上传幂等键；仅用于同一候选人的上传重试，不向 API 返回 |
| file_name    | VARCHAR(255)      | NO       | 无                | 文件名称     |
| stored_file_object_id | UUID      | NO       | 无                | 内部文件对象引用 |
| file_type    | VARCHAR           | NO       | 无                | 文件类型 |
| parse_status | parse_status_enum | NO       | processing        | 解析状态     |
| created_at   | TIMESTAMPTZ       | NO       | CURRENT_TIMESTAMP | 创建时间     |

2. 外键约束

| Constraint Name      | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| -------------------- | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_resume_candidate | candidate_id | 求职者表         | id                | CASCADE   | 简历所属的求职者     |
| fk_resume_stored_file_object | stored_file_object_id | 内部文件对象表 | id | RESTRICT | 简历引用的底层对象 |

3. 索引Indexes

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_resume_candidate | candidate_id | INDEX   |
| uq_resume_candidate_upload_idempotency_key | candidate_id, upload_idempotency_key | UNIQUE（`upload_idempotency_key IS NOT NULL`） |
| idx_resume_stored_file_object | stored_file_object_id | INDEX |

`resumes` 保存原始文件引用、归属与解析生命周期，不保存 `parse_data` 等重复结构化结果；可用的简历结构化事实只写入同一简历对应的 `candidate_profiles`。

### 求职者画像表（`candidate_profiles`，`MVP`）

1. 表结构

| Column                     | Type         | Nullable | Default           | Description  |
| -------------------------- | ------------ | -------- | ----------------- | ------------ |
| id                         | UUID         | NO       | gen_random_uuid() | 主键         |
| resume_id                  | UUID         | NO       | 无                | 来源简历     |
| target_job_titles          | VARCHAR(128)[] | NO     | 无                | 从成功解析简历提取的目标岗位名称列表；至少一个非空元素，不是推荐结果 |
| skills                     | JSONB        | YES      | NULL              | 技能列表     |
| work_experience_summary    | JSONB        | YES      | NULL              | 工作经历摘要 |
| project_experience_summary | JSONB        | YES      | NULL              | 项目经历摘要 |
| years_of_experience        | INT          | YES      | NULL              | 工作年限     |
| education                  | VARCHAR(64)  | YES      | NULL              | 学历         |
| expected_location          | VARCHAR(128) | YES      | NULL              | 期望地点     |
| expected_salary            | VARCHAR(64)  | YES      | NULL              | 期望薪资     |
| created_at                 | TIMESTAMPTZ  | NO       | CURRENT_TIMESTAMP | 创建时间     |

2. 外键约束

| Constraint Name                | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| ------------------------------ | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_candidate_profile_resume    | resume_id    | 简历表           | id                | CASCADE   | 画像生成时使用的简历 |

3. 索引Indexes

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| uq_candidate_profile_resume | resume_id | UNIQUE |
| ck_candidate_profile_target_job_titles_nonempty | `cardinality(target_job_titles) >= 1` | CHECK |

### 异步任务运行表（`async_task_runs`，`MVP`）

1. 表结构

| Column | Type | Nullable | Default | Description |
| --- | --- | --- | --- | --- |
| id | UUID | NO | gen_random_uuid() | 主键 |
| task_type | async_task_type_enum | NO | 无 | 业务任务类型 |
| resource_type | async_task_resource_type_enum | NO | 无 | 被处理资源类型 |
| resource_id | UUID | NO | 无 | 被处理资源 ID；归属由对应资源链推导 |
| celery_task_id | VARCHAR(255) | YES | NULL | Celery 已接受投递后的任务标识；`queued` 且为空表示待可靠投递 |
| idempotency_key | VARCHAR(255) | NO | 无 | 固定为 `{task_type}:{resource_id}:{task_version}` 的确定性幂等标识；不含文件名、文件内容或随机值 |
| status | async_task_run_status_enum | NO | queued | 业务任务运行状态 |
| task_version | VARCHAR(128) | NO | 无 | MVP 固定为内部常量 `v1`，用于既有幂等键；不提供版本管理能力 |
| failure_code | parse_failure_code_enum | YES | NULL | 解析任务终态失败的脱敏分类；是解析资源失败原因的唯一权威来源；成功时为空 |
| created_at | TIMESTAMPTZ | NO | CURRENT_TIMESTAMP | 任务运行记录创建时间 |
| started_at | TIMESTAMPTZ | YES | NULL | 当前一次实际执行取得数据库租约的时间；排队和终态时为空 |
| execution_token | UUID | YES | NULL | 当前执行租约的不可预测围栏令牌；排队和终态时为空，不向 API 返回 |
| execution_lease_expires_at | TIMESTAMPTZ | YES | NULL | 当前执行租约的到期时间；用于异常重领与卡死兜底，不向 API 返回 |
| finished_at | TIMESTAMPTZ | YES | NULL | 终态完成时间；未终态时为空 |

2. 外键约束

`async_task_runs` 使用 `resource_type + resource_id` 关联多种异步资源，不能设置单一数据库外键。具体的可靠入队、Dispatcher、Worker、重试和超时机制以 [异步任务技术方案](../04-technical-solutions/Async%20task%20technical%20design.md) 为准。

3. 索引

| Name | Columns | Type |
| --- | --- | --- |
| PRIMARY | id | PRIMARY |
| uq_async_task_run_celery_task | celery_task_id | UNIQUE |
| uq_async_task_run_idempotency | resource_type, resource_id, task_type, task_version, idempotency_key | UNIQUE |
| idx_async_task_run_stalled_scan | status, started_at | INDEX |
| ck_async_task_run_celery_id_before_execution | `status = 'queued' OR celery_task_id IS NOT NULL` | CHECK |
| idx_async_task_run_resource | resource_type, resource_id | INDEX |
| idx_async_task_run_status | status | INDEX |
| idx_async_task_run_pending_dispatch | created_at | PARTIAL INDEX (`status = 'queued' AND celery_task_id IS NULL`) |

`candidate_profiles` 仅保存已成功解析简历的确定性派生结果，也是 MVP 下游读取简历结构化事实的唯一表。`target_job_titles` 必须由简历结构化解析提供，并以 `VARCHAR(128)[]` 非空数组存储；单个职位也存为单元素数组。画像不作为独立异步任务运行；`candidate_documents` 不创建 `AsyncTaskRun`，也不保存解析状态或解析结果。简历解析的 MinerU MCP 调用、内存 Schema 与失败映射以[简历解析技术方案](../04-technical-solutions/Resume%20parsing%20technical%20design.md)为准。

### 求职者资料表（`candidate_documents`，`MVP`）

1. 表结构

| Column        | Type         | Nullable | Default           | Description |
| ------------- | ------------ | -------- | ----------------- | ----------- |
| id            | UUID         | NO       | gen_random_uuid() | 主键        |
| candidate_id  | UUID         | NO       | 无                | 求职者ID    |
| upload_idempotency_key | UUID | YES | NULL | 客户端上传幂等键；仅用于同一候选人的上传重试，不向 API 返回 |
| document_type | document_type_enum | NO    | 无                | 文档类型    |
| document_name | VARCHAR(255) | NO       | 无                | 文档名称    |
| file_type    | VARCHAR           | NO       | 无                | 文件类型 |
| stored_file_object_id | UUID | NO | 无 | 内部文件对象引用 |
| created_at    | TIMESTAMPTZ  | NO       | CURRENT_TIMESTAMP | 创建时间    |

2. 外键约束

| Constraint Name        | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| ---------------------- | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_candidate_document | candidate_id | 求职者表         | id                | CASCADE   | 资料所属的求职者     |
| fk_candidate_document_stored_file_object | stored_file_object_id | 内部文件对象表 | id | RESTRICT | 资料引用的底层对象 |

3. 索引

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_candidate_document_candidate | candidate_id | INDEX   |
| uq_candidate_document_candidate_upload_idempotency_key | candidate_id, upload_idempotency_key | UNIQUE（`upload_idempotency_key IS NOT NULL`） |
| idx_candidate_document_stored_file_object | stored_file_object_id | INDEX |

### 求职目标表（`job_goals`，`MVP`）

1. 表结构

| Column              | Type        | Nullable | Default           | Description   |
| ------------------- | ----------- | -------- | ----------------- | ------------- |
| id                  | UUID        | NO       | gen_random_uuid() | 主键          |
| candidate_id        | UUID        | NO       | 无                | 求职者ID      |
| target_offer_count  | INT         | NO       | 1                 | 目标Offer数量 |
| current_offer_count | INT         | NO       | 0                 | 当前Offer数量 |
| status              | job_goal_status_enum | NO | active            | 状态          |
| created_at          | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 创建时间 |
| filter_conditions        | JSONB | NO       | 无 | 岗位过滤条件；JSON 对象，`include`、`exclude` 及全部子字段均可省略 |

`filter_conditions` 的结构与业务模型中 `Filter Conditions` 一致：可选的
`include.job_nature`、`exclude.locations`、`exclude.employment_type`、
`exclude.interview_mode` 均为字符串数组。未提供的字段不参与过滤。

2. 外键约束

| Constraint Name      | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| -------------------- | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_job_goal_candidate | candidate_id | 求职者表       | id                | CASCADE   | 求职目标所属的求职者 |

3. 索引

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_job_goal_candidate | candidate_id | INDEX   |

### 岗位表（`jobs`，`MVP`）

1. 表结构

| Column          | Type        | Nullable | Default           | Description |
| --------------- | ----------- | -------- | ----------------- | ----------- |
| id              | UUID        | NO       | gen_random_uuid() | 主键        |
| title           | TEXT        | NO       | 无                | 岗位名称    |
| company_name    | TEXT        | YES      | NULL              | 企业名称    |
| location        | TEXT        | YES      | NULL              | 工作地点    |
| salary_range    | VARCHAR(64) | YES      | NULL              | 薪资范围    |
| job_nature      | VARCHAR(64) | YES      | NULL              | 岗位性质    |
| employment_type | VARCHAR(64) | YES      | NULL              | 雇佣模式    |
| interview_mode  | VARCHAR(64) | YES      | NULL              | 面试形式    |
| created_at      | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 创建时间    |

3. 索引

| Name    | Columns | Type    |
| ------- | ------- | ------- |
| PRIMARY | id      | PRIMARY |

### 岗位JD表（`job_descriptions`，`MVP`）

1. 表结构

| Column           | Type              | Nullable | Default           | Description |
| ---------------- | ----------------- | -------- | ----------------- | ----------- |
| id               | UUID              | NO       | gen_random_uuid() | 主键        |
| job_id           | UUID              | NO       | 无                | 岗位ID      |
| raw_content      | TEXT              | NO       | 无                | JD原文      |
| responsibilities | JSONB             | YES      | NULL              | 工作职责    |
| requirements     | JSONB             | YES      | NULL              | 任职要求    |
| parse_data       | JSONB             | YES      | NULL              | JD解析结构  |
| parse_status     | parse_status_enum | NO       | processing        | 解析状态    |
| created_at       | TIMESTAMPTZ       | NO       | CURRENT_TIMESTAMP | 创建时间    |

2. 外键约束

| Constraint Name | Local Column | Referenced Table | Referenced Column | On Delete | Description   |
| --------------- | ------------ | ---------------- | ----------------- | --------- | ------------- |
| fk_job_jd_job   | job_id       | 岗位表           | id                | CASCADE   | JD 所属的岗位 |

3. 索引

| Name    | Columns | Type    |
| ------- | ------- | ------- |
| PRIMARY | id      | PRIMARY |
| idx_job_jd_job | job_id | INDEX   |

### 岗位轮次匹配表（`match_runs`，`MVP`）

1. 表结构

| Column       | Type        | Nullable | Default           | Description  |
| ------------ | ----------- | -------- | ----------------- | ------------ |
| id           | UUID        | NO       | gen_random_uuid() | 主键         |
| job_goal_id  | UUID        | NO       | 无                | 求职目标；候选人归属锚点 |
| resume_id    | UUID        | NO       | 无                | 使用简历     |
| status       | match_run_status_enum | NO | running           | 执行状态     |
| result_count | INT         | YES      | NULL              | 本次匹配批次生成的结果数量 |
| created_at   | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 创建时间     |

2. 外键约束

| Constraint Name              | Local Column | Referenced Table | Referenced Column | On Delete | Description              |
| ---------------------------- | ------------ | ---------------- | ----------------- | --------- | ------------------------ |
| fk_match_run_job_goal        | job_goal_id  | 求职目标表       | id                | RESTRICT  | 匹配任务关联的求职目标及候选人归属锚点 |
| fk_match_run_resume          | resume_id    | 简历表           | id                | RESTRICT  | 匹配任务使用的简历       |

3. 索引

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_match_run_job_goal | job_goal_id | INDEX   |

### 匹配结果表（`match_results`，`MVP`）

1. 表结构

| Column                | Type        | Nullable | Default           | Description  |
| --------------------- | ----------- | -------- | ----------------- | ------------ |
| id                    | UUID        | NO       | gen_random_uuid() | 主键         |
| match_run_id          | UUID        | NO       | 无                | 匹配批次     |
| profile_id            | UUID        | NO       | 无                | 使用的求职者画像版本 |
| job_id                | UUID        | NO       | 无                | 岗位ID       |
| recall_score          | NUMERIC     | NO       | 无                | 召回阶段分  |
| skill_match_score | NUMERIC     | NO      | 无              | 技能匹配分  |
| experience_match_score | NUMERIC     | NO      | 无              | 经验匹配分   |
| salary_match_score | NUMERIC | NO | 无 | 薪资匹配分 |
| final_match_score | NUMERIC     | NO      | 无              | 综合匹配分 |
| algorithm_version     | VARCHAR     | NO      | 无              | 匹配算法版本 |
| recommendation_reason | TEXT        | NO      | 无              | 推荐理由     |
| created_at            | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 创建时间     |

2. 外键约束

| Constraint Name        | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| ---------------------- | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_match_result_run   | match_run_id | 岗位轮次匹配表   | id                | CASCADE   | 匹配结果所属的匹配批次 |
| fk_match_result_profile | profile_id | 求职者画像表     | id                | RESTRICT  | 匹配结果使用的画像版本 |
| fk_match_result_job   | job_id       | 岗位表           | id                | RESTRICT  | 匹配结果对应的岗位     |

3. 索引

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_match_result_run | match_run_id | INDEX   |
| idx_match_result_profile | profile_id | INDEX   |
| uq_match_result_run_job | match_run_id, job_id | UNIQUE |

匹配结果仅在评分和解释均生成完成后写入。`algorithm_version` 必须标识实际使用的算法、规则及提示词版本组合；同一 `match_run` 内的结果必须使用相同版本。任务失败时仅更新匹配批次状态和失败原因，不得写入不完整的匹配结果。

### 岗位申请表（`applications`，`MVP`）

1. 表结构

| Column          | Type                       | Nullable | Default           | Description  |
| --------------- | -------------------------- | -------- | ----------------- | ------------ |
| id              | UUID                       | NO       | gen_random_uuid() | 主键         |
| job_id          | UUID                       | NO       | 无                | 岗位ID       |
| goal_id         | UUID                       | NO       | 无                | 求职目标ID；候选人归属锚点 |
| resume_id       | UUID                       | NO       | 无                | 投递简历     |
| match_result_id | UUID                       | YES      | NULL              | 来源匹配结果 |
| status          | job_application_enum | NO       | created           | 当前状态     |
| applied_at      | TIMESTAMPTZ                | YES      | NULL              | 投递时间     |
| created_at      | TIMESTAMPTZ                | NO       | CURRENT_TIMESTAMP | 创建时间     |

2. 外键约束

| Constraint Name                  | Local Column    | Referenced Table | Referenced Column | On Delete | Description              |
| -------------------------------- | --------------- | ---------------- | ----------------- | --------- | ------------------------ |
| fk_application_job               | job_id          | 岗位表           | id                | RESTRICT  | 投递记录对应的岗位       |
| fk_application_goal              | goal_id         | 求职目标表       | id                | RESTRICT  | 投递记录所属的求职目标及候选人归属锚点 |
| fk_application_resume            | resume_id       | 简历表           | id                | RESTRICT  | 投递时使用的简历         |
| fk_application_match_result      | match_result_id | 匹配结果表       | id                | SET NULL  | 投递来源的匹配结果       |

3. 索引

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_application_job | job_id | INDEX   |
| idx_application_goal | goal_id | INDEX   |

### 沟通会话表（`conversations`，`MVP`）

1. 表结构

| Column          | Type        | Nullable | Default           | Description  |
| --------------- | ----------- | -------- | ----------------- | ------------ |
| id              | UUID        | NO       | gen_random_uuid() | 主键         |
| application_id  | UUID        | NO       | 无                | 投递记录     |
| summary         | TEXT        | NO       | 无                | 会话摘要     |
| created_at      | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 创建时间     |
| last_message_at | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 最后更新时间 |

`last_message_at` 由 PostgreSQL `AFTER INSERT` 消息触发器维护：共用函数
`set_conversation_last_message_at()` 将所属会话更新为 `NEW.created_at`。Repository、
Service 和 Agent 不得手动设置该字段。

2. 外键约束

| Constraint Name              | Local Column   | Referenced Table | Referenced Column | On Delete | Description          |
| ---------------------------- | -------------- | ---------------- | ----------------- | --------- | -------------------- |
| fk_conversation_application  | application_id | 岗位申请表       | id                | CASCADE   | 会话关联的投递记录及候选人归属锚点 |

3. 索引

| Name            | Columns        | Type    |
| --------------- | -------------- | ------- |
| PRIMARY         | id             | PRIMARY |
| idx_conversation_application | application_id | INDEX   |

### 消息表（`messages`，`MVP`）

1. 表结构

| Column          | Type        | Nullable | Default           | Description    |
| --------------- | ----------- | -------- | ----------------- | -------------- |
| id              | UUID        | NO       | gen_random_uuid() | 主键           |
| conversation_id | UUID        | NO       | 无                | 会话ID         |
| role            | message_role_enum | NO   | 无                | 消息角色       |
| content         | TEXT        | NO       | 无                | 消息内容       |
| intent          | message_intent_enum | YES | NULL              | 意图分类       |
| created_at      | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 创建时间       |

2. 外键约束

| Constraint Name          | Local Column    | Referenced Table | Referenced Column | On Delete | Description      |
| ------------------------ | --------------- | ---------------- | ----------------- | --------- | ---------------- |
| fk_message_conversation | conversation_id | 沟通会话表       | id                | CASCADE   | 消息所属的会话   |

3. 索引

| Name             | Columns         | Type    |
| ---------------- | --------------- | ------- |
| PRIMARY          | id              | PRIMARY |
| idx_message_conversation | conversation_id | INDEX   |

### 消息附件表（`message_attachments`，`MVP`）

1. 表结构

| Column        | Type               | Nullable | Default           | Description              |
| ------------- | ------------------ | -------- | ----------------- | ------------------------ |
| id            | UUID               | NO       | gen_random_uuid() | 主键                     |
| message_id    | UUID               | NO       | 无                | 所属消息；附件归属锚点   |
| candidate_document_id | UUID        | NO       | 无                | 被消息引用的候选人附加资料 |
| created_at    | TIMESTAMPTZ        | NO       | CURRENT_TIMESTAMP | 引用创建时间             |

2. 外键约束

| Constraint Name       | Local Column | Referenced Table | Referenced Column | On Delete | Description  |
| --------------------- | ------------ | ---------------- | ----------------- | --------- | ------------ |
| fk_attachment_message | message_id   | 消息表           | id                | CASCADE   | 附件所属消息 |
| fk_attachment_candidate_document | candidate_document_id | 求职者资料表 | id | RESTRICT | 附件引用候选人资料 |

3. 索引

| Name        | Columns    | Type    |
| ----------- | ---------- | ------- |
| PRIMARY     | id         | PRIMARY |
| idx_attachment_message | message_id | INDEX   |
| idx_attachment_candidate_document | candidate_document_id | INDEX |
| uq_attachment_message_document | message_id, candidate_document_id | UNIQUE |

消息附件只表示候选人附加资料在某条消息中的引用。Repository 必须经 `message → conversation → application → goal → candidate` 与 `candidate_document.candidate_id` 原子校验二者归属一致，并校验资料对象存在；不得复制、重新解析附件文件或将其正文提供给 Agent/LLM。

### 求职进度事件表（`progress_events`，`MVP`）

1. 表结构

| Column         | Type        | Nullable | Default           | Description |
| -------------- | ----------- | -------- | ----------------- | ----------- |
| id             | UUID        | NO       | gen_random_uuid() | 主键        |
| application_id | UUID        | NO       | 无                | 投递记录    |
| from_stage     | delivery_progress_enum | YES | NULL              | 原状态      |
| to_stage       | delivery_progress_enum | NO  | 无                | 新状态      |
| description    | TEXT        | YES      | NULL              | 事件描述    |
| created_at     | TIMESTAMPTZ | NO       | CURRENT_TIMESTAMP | 创建时间    |

2. 外键约束

| Constraint Name            | Local Column   | Referenced Table | Referenced Column | On Delete | Description            |
| -------------------------- | -------------- | ---------------- | ----------------- | --------- | ---------------------- |
| fk_progress_event_application | application_id | 岗位申请表     | id                | CASCADE   | 事件关联的投递记录     |

3. 索引

| Name            | Columns        | Type    |
| --------------- | -------------- | ------- |
| PRIMARY         | id             | PRIMARY |
| idx_progress_event_application | application_id | INDEX   |

## 枚举类型定义

### parse_status_enum

| 值         | 含义     |
| ---------- | -------- |
| processing | 解析中   |
| succeeded  | 解析成功；对正式简历表示对应候选人画像已在同一事务中原子写入 |
| failed     | 解析失败；对正式简历包含画像生成、校验或原子写入失败 |

### document_type_enum

| 值           | 含义         |
| ------------ | ------------ |
| job_strategy | 求职策略文档 |
| certificate  | 证书材料     |
| other        | 其它资料     |

### async_task_type_enum

| 值 | 含义 |
| --- | --- |
| resume_parse | 简历解析 |
| job_description_parse | 岗位 JD 解析 |
| job_matching | 岗位匹配 |

### stored_file_object_status_enum

| 值 | 含义 |
| --- | --- |
| writing | 对象目录记录已建立，正式文件写入或资源建档尚未完成；不得被业务资源引用 |
| ready | 正式文件存在且可受控读取 |
| deleting | 已被清理任务锁定并等待或正在删除；不得创建新引用 |

### async_task_resource_type_enum

| 值 | 含义 |
| --- | --- |
| resume | 简历资源 |
| job_description | 岗位 JD 资源 |
| match_run | 岗位匹配批次资源 |

### async_task_run_status_enum

| 值 | 含义 |
| --- | --- |
| queued | 已提交但尚待 Dispatcher 投递，或已由 Celery 接受但正在等待执行/重试 |
| running | Worker 已取得有效执行权 |
| succeeded | 已完成完整业务结果持久化 |
| failed | 已重试耗尽或发生确定性失败 |

### parse_failure_code_enum

| 值 | 含义 |
| --- | --- |
| unsupported_file | 不支持的文件格式 |
| file_unreadable | 文件损坏或无法读取 |
| storage_unavailable | 对象存储不可用且重试耗尽 |
| parser_timeout | 解析服务超时且重试耗尽 |
| schema_validation_failed | 解析或模型输出未通过结构化校验 |
| internal_error | 未分类内部错误 |


### job_goal_status_enum

| 值           | 含义         |
| ------------ | ------------ |
| active | 求职目标已激活 |
| achieved  | 求职目标已完成     |
| abandoned | 求职目标已废弃     |

### match_run_status_enum

| 值        | 含义     |
| --------- | -------- |
| running | 匹配执行中 |
| completed    | 匹配完成 |
| failed    | 匹配失败 |


### message_intent_enum

| 值        | 含义     |
| --------- | -------- |
| profile_request | 资料请求 |
| job_inquiry    | 岗位相关咨询 |
| salary_discussion    | 薪资沟通 |
| interview_schedule    | 薪资沟通 |
| application_status    | 投递进度 |
| general_chat    | 其它闲聊 |

### delivery_progress_enum

| 值        | 含义     |
| --------- | -------- |
| submitted | 已申请 |
| screening | 初筛中 |
| written_test | 笔试 |
| interview_1   | 一面 |
| interview_2   | 二面 |
| interview_3   | 三面 |
| hr_interview | HR面 |
| offer | 获得Offer |
| terminated | 流程终止 |


### message_role_enum

| 值        | 含义     |
| --------- | -------- |
| candidate | Candidate Agent 代表求职者生成或发送的消息 |
| hr | HR发送的消息（当前不存在，模拟替代） |


### job_application_enum

| 值        | 含义     |
| --------- | -------- |
| created| 申请记录已创建 |
| applied | 岗位已投递 |
