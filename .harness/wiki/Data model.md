





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

范围裁决以 `.harness/wiki/MVP scope and development boundaries.md` 为最高依据。`Deferred` 对象可保留在数据模型中供后续阶段使用，但不得作为 MVP 的迁移前置条件。

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

### 简历表（`resumes`，`MVP`）

1. 表结构

| Column       | Type              | Nullable | Default           | Description  |
| ------------ | ----------------- | -------- | ----------------- | ------------ |
| id           | UUID              | NO       | gen_random_uuid() | 主键         |
| candidate_id | UUID              | NO       | 无                | 求职者ID     |
| file_name    | VARCHAR(255)      | NO       | 无                | 文件名称     |
| file_url     | VARCHAR(512)      | NO       | 无                | 文件地址     |
| file_type    | VARCHAR           | NO       | 无                | 文件类型 |
| parse_status | parse_status_enum | NO       | processing        | 解析状态     |
| parse_error  | TEXT              | YES      | NULL              | 解析错误信息 |
| created_at   | TIMESTAMPTZ       | NO       | CURRENT_TIMESTAMP | 创建时间     |

2. 外键约束

| Constraint Name      | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| -------------------- | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_resume_candidate | candidate_id | 求职者表         | id                | CASCADE   | 简历所属的求职者     |

3. 索引Indexes

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_resume_candidate | candidate_id | INDEX   |

### 求职者画像表（`candidate_profiles`，`MVP`）

1. 表结构

| Column                     | Type         | Nullable | Default           | Description  |
| -------------------------- | ------------ | -------- | ----------------- | ------------ |
| id                         | UUID         | NO       | gen_random_uuid() | 主键         |
| resume_id                  | UUID         | NO       | 无                | 来源简历     |
| target_job_titles          | VARCHAR(128) | YES      | NULL              | 目标岗位名称 |
| skills                     | JSONB        | YES      | NULL              | 技能列表     |
| work_experience_summary    | JSONB        | YES      | NULL              | 工作经历摘要 |
| project_experience_summary | JSONB        | YES      | NULL              | 项目经历摘要 |
| years_of_experience        | INT          | YES      | NULL              | 工作年限     |
| education                  | VARCHAR(64)  | YES      | NULL              | 学历         |
| expected_location          | VARCHAR(128) | YES      | NULL              | 期望地点     |
| expected_salary            | VARCHAR(64)  | YES      | NULL              | 期望薪资     |
| embedding_id               | VARCHAR(128) | YES      | NULL              | 向量索引ID   |
| created_at                 | TIMESTAMPTZ  | NO       | CURRENT_TIMESTAMP | 创建时间     |

2. 外键约束

| Constraint Name                | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| ------------------------------ | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_candidate_profile_resume    | resume_id    | 简历表           | id                | CASCADE   | 画像生成时使用的简历 |

3. 索引Indexes

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_candidate_profile_resume | resume_id | INDEX   |

### 求职者资料表（`candidate_documents`，`Deferred`）

1. 表结构

| Column        | Type         | Nullable | Default           | Description |
| ------------- | ------------ | -------- | ----------------- | ----------- |
| id            | UUID         | NO       | gen_random_uuid() | 主键        |
| candidate_id  | UUID         | NO       | 无                | 求职者ID    |
| document_type | document_type_enum | NO    | 无                | 文档类型    |
| document_name | VARCHAR(255) | NO       | 无                | 文档名称    |
| parse_data       | JSONB       | YES      | NULL              | 求职资料解析结构 |
| parse_error  | TEXT              | YES      | NULL              | 解析错误信息 |
| parse_status | parse_status_enum | NO       | processing | 解析状态    |
| file_type    | VARCHAR           | NO       | 无                | 文件类型 |
| file_url      | VARCHAR(512) | NO       | 无                | 文件地址    |
| created_at    | TIMESTAMPTZ  | NO       | CURRENT_TIMESTAMP | 创建时间    |

2. 外键约束

| Constraint Name        | Local Column | Referenced Table | Referenced Column | On Delete | Description          |
| ---------------------- | ------------ | ---------------- | ----------------- | --------- | -------------------- |
| fk_candidate_document | candidate_id | 求职者表         | id                | CASCADE   | 资料所属的求职者     |

3. 索引

| Name          | Columns      | Type    |
| ------------- | ------------ | ------- |
| PRIMARY       | id           | PRIMARY |
| idx_candidate_document_candidate | candidate_id | INDEX   |

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

### 消息附件表（`message_attachments`，`Deferred`）

1. 表结构

| Column        | Type               | Nullable | Default           | Description              |
| ------------- | ------------------ | -------- | ----------------- | ------------------------ |
| id            | UUID               | NO       | gen_random_uuid() | 主键                     |
| message_id    | UUID               | NO       | 无                | 所属消息；附件归属锚点   |
| document_type | document_type_enum | NO       | 无                | 附件资料类型             |
| document_name | VARCHAR(255)       | NO       | 无                | 附件名称                 |
| file_url      | VARCHAR(512)       | NO       | 无                | 文件地址                 |
| file_type     | VARCHAR            | NO       | 无                | 文件类型                 |
| parse_data    | JSONB              | YES      | NULL              | 附件解析结构             |
| parse_error   | TEXT               | YES      | NULL              | 附件解析错误信息         |
| parse_status  | parse_status_enum  | NO       | processing        | 附件解析状态             |
| created_at    | TIMESTAMPTZ        | NO       | CURRENT_TIMESTAMP | 创建时间                 |

2. 外键约束

| Constraint Name       | Local Column | Referenced Table | Referenced Column | On Delete | Description  |
| --------------------- | ------------ | ---------------- | ----------------- | --------- | ------------ |
| fk_attachment_message | message_id   | 消息表           | id                | CASCADE   | 附件所属消息 |

3. 索引

| Name        | Columns    | Type    |
| ----------- | ---------- | ------- |
| PRIMARY     | id         | PRIMARY |
| idx_attachment_message | message_id | INDEX   |

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
| succeeded  | 解析成功 |
| failed     | 解析失败 |

### document_type_enum

| 值           | 含义         |
| ------------ | ------------ |
| job_strategy | 求职策略文档 |
| certificate  | 证书材料     |
| other        | 其它资料     |


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
