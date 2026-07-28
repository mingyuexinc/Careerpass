# 接口协议

## 通用约定

### Base URL
```
Development:http://localhost:8080
Production:TBD
```

### 请求头

|  Header |  Required  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  content-Type | 请求包含正文时必填 | 默认 `application/json`；文件上传接口使用 `multipart/form-data` |
|  Authorization| 除认证公开接口外均必填 | Bearer {access_token}；`/api/v1/auth/register`、`/api/v1/auth/login`、`/api/v1/auth/refresh` 无需此请求头 |
|  X-Request-ID | No | 请求追踪ID | 
| `Idempotency-Key` | 文件上传时推荐 | 客户端生成的 UUID；同一候选人对同一上传端点的同一请求重试复用首次创建结果。非 UUID 值返回 `ErrorCode.INVALID_REQUEST (400)` |


### 统一响应格式

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  code | Integer | 与 HTTP 状态一致的业务状态码；由 `ErrorCode` 统一映射 |
|  msg | String | 由 `ErrorCode` 统一映射的受控、脱敏场景描述；不得作为客户端程序分支依据 |
|  data | T / null | 成功时为业务数据；失败时默认为 `null`，仅在契约明确允许时返回脱敏的附加数据 |

- 成功响应示例：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```


### 分页响应

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "list": [],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### 错误码与 HTTP 映射

后端使用统一的 `ErrorCode` 枚举。每个枚举值固定映射 HTTP 状态、响应体 `code` 与 `msg`；响应体 `code` 必须与 HTTP 状态一致。业务代码仅抛出 `BusinessException(ErrorCode.<NAME>)`，由全局异常处理器生成响应。

| ErrorCode | HTTP 状态 / 响应 `code` | `msg` | 使用场景 |
| --- | --- | --- | --- |
| `SUCCESS` | `200` | `success` | 查询或已完成的同步操作成功 |
| `UPLOAD_ACCEPTED` | `201` | `上传已受理，正在解析简历` | 正式简历资源与解析任务已创建，尚未承诺解析成功 |
| `UPLOAD_SUCCEEDED` | `201` | `上传成功` | 不进入异步解析的候选人附加资料上传成功 |
| `MATCHING_STARTED` | `200` | `匹配任务已启动` | 岗位匹配异步任务已创建，尚未承诺匹配结果 |
| `INVALID_REQUEST` | `400` | `请求参数或文件格式不符合要求` | 必填字段缺失、分页参数非法、扩展名/MIME/文件特征校验失败 |
| `UNAUTHORIZED` | `401` | `登录状态无效或已过期` | 缺失、无效或过期的访问令牌 |
| `RESOURCE_NOT_FOUND` | `404` | `资源不存在或暂不可用` | 资源不存在、资源不归属当前候选人、指定简历尚无可用画像 |
| `PRECONDITION_NOT_MET` | `409` | `当前操作尚未满足前置条件` | 匹配、投递或沟通中指定资源、目标状态或授权条件不满足模块自身前置条件 |
| `IDEMPOTENCY_KEY_CONFLICT` | `409` | `幂等键与请求内容不一致` | 同一候选人对同一上传端点复用已有 `Idempotency-Key`，但文件内容或展示名不同 |
| `FILE_TOO_LARGE` | `413` | `文件大小超过 10 MB` | 上传文件超过 10,000,000 bytes 限制 |
| `INTERNAL_ERROR` | `500` | `服务暂时不可用，请稍后重试` | 未分类内部错误；不得暴露堆栈、路径或供应商原始错误 |

`FILE_NOT_FOUND` 等资源细分错误可作为内部 `ErrorCode` 使用，但对候选人资源的对外响应必须映射为 `RESOURCE_NOT_FOUND`，避免泄露资源存在性。`parse_failure_code` 用于已接受资源的异步解析终态，不是 HTTP 错误码：查询列表本身成功时仍返回 `200 / success`，失败分类仅通过列表项的 `failure_code` 返回。

错误响应示例：

```json
{
  "code": 413,
  "msg": "文件大小超过 10 MB",
  "data": null
}
```

### 版本适用范围

| 标记 | 含义 |
| --- | --- |
| `MVP` | 当前 MVP 必须实现、测试并纳入验收的接口能力。 |
| `Deferred` | 已完成设计但不属于当前 MVP 实现范围的后续能力；不得作为 MVP 开发依赖或验收条件。 |

未单独标记的既有接口，适用范围以所属模块或其所在章节的标记为准。范围裁决以 `.harness/wiki/01-governance/MVP scope and development boundaries.md` 为最高依据。

## 模块API

### 认证与会话管理模块（`MVP` 与 `Deferred`）

#### 注册账号

- 版本：`MVP`

- 接口：POST /api/v1/auth/register

- Authorization：不需要

- Request Body：

| Param | Type | Required | Description |
| --- | --- | --- | --- |
| username | String | Yes | 用户名，唯一，长度与字符规则由服务端校验 |
| password | String | Yes | 明文密码，仅用于本次传输；服务端不得保存或返回明文 |
| name | String | No | 候选人姓名；未提供时创建姓名为空的候选人 |

```json
{
    "username":"alice",
    "password":"ExamplePassword123!",
    "name":"Alice"
}
```

- 处理规则：用户名唯一校验通过后，在同一事务中创建 `users` 账户和唯一关联的 `candidates` 记录；成功后签发令牌。

- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "access_token":"<access_token>",
        "refresh_token":"<refresh_token>",
        "token_type":"Bearer",
        "expires_in":1800,
        "user":{
            "user_id":"user_001",
            "candidate_id":"candidate_001"
        }
    }
}
```

#### 登录

- 版本：`MVP`

- 接口：POST /api/v1/auth/login

- Authorization：不需要

- Request Body：

| Param | Type | Required | Description |
| --- | --- | --- | --- |
| username | String | Yes | 用户名 |
| password | String | Yes | 明文密码，仅用于本次传输 |

```json
{
    "username":"alice",
    "password":"ExamplePassword123!"
}
```

- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "access_token":"<access_token>",
        "refresh_token":"<refresh_token>",
        "token_type":"Bearer",
        "expires_in":1800,
        "user":{
            "user_id":"user_001",
            "candidate_id":"candidate_001"
        }
    }
}
```

#### 刷新访问令牌

- 版本：`Deferred`

- 接口：POST /api/v1/auth/refresh

- Authorization：不需要

- Request Body：

| Param | Type | Required | Description |
| --- | --- | --- | --- |
| refresh_token | String | Yes | 登录或上一次刷新签发的 Refresh Token |

```json
{
    "refresh_token":"<refresh_token>"
}
```

- 处理规则：校验 Refresh Token 的有效期、撤销状态和所属用户；成功后轮换 Refresh Token，旧 Token 立即失效。本接口不创建用户或候选人，不校验用户名和密码。

- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "access_token":"<new_access_token>",
        "refresh_token":"<new_refresh_token>",
        "token_type":"Bearer",
        "expires_in":1800
    }
}
```

#### 退出登录

- 版本：`Deferred`

- 接口：POST /api/v1/auth/logout

- Request Body：

| Param | Type | Required | Description |
| --- | --- | --- | --- |
| refresh_token | String | Yes | 要撤销的当前会话 Refresh Token |

```json
{
    "refresh_token":"<refresh_token>"
}
```

- 处理规则：仅允许撤销当前已认证用户所属的 Refresh Token；撤销后该 Token 不可用于刷新 Access Token。

- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{}
}
```

#### 获取当前登录用户

- 版本：`MVP`

- 接口：GET /api/v1/auth/me

- Query Parameters：无

- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "user_id":"user_001",
        "username":"alice",
        "candidate_id":"candidate_001",
        "name":"Alice"
    }
}
```

### 求职目标管理模块（`MVP`）

#### 获取当前求职目标

- 接口：GET /api/v1/job-goals/current

- Query Parameters：无


- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "goal_id":"goal_001",
        "target_offer_count":3,
        "current_offer_count":1,
        "status":"active",
        "created_at":"2026-07-18T10:00:00"
    }
}
```

#### 创建求职目标

- 接口：POST /api/v1/job-goals

- Request Body：

| Param | Type | Required | Description |
| --- | --- | --- | --- |
| target_offer_count | Integer | No | 目标 Offer 数量，默认值为 1 |
| filter_conditions | JSON | Yes | 岗位过滤条件对象；可传入 `{}`，其内部 `include`、`exclude` 及全部子字段均可省略 |

```json
{
    "target_offer_count": 3,
    "filter_conditions": {
        "include": {
            "job_nature": ["fulltime"]
        },
        "exclude": {
            "locations": ["北京"],
            "employment_type": ["outsource"],
            "interview_mode": ["offline"]
        }
    }
}
```

- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "goal_id":"goal_001",
        "status":"active"
    }
}
```
### 简历管理模块（`MVP`）

#### 上传简历

- 接口：POST /api/v1/resumes
- Content-Type：`multipart/form-data`
- 请求头：推荐携带 `Idempotency-Key: <UUID>`；相同候选人对本端点使用相同 Key 且文件内容、规范化后的 `name` 均相同时，服务端必须重放首次 `201` 响应，即返回首次创建的 `resume_id` 和 `parse_status: processing`，不返回资源当前解析状态。有意重新上传必须使用新的 Key，仍创建新的简历资源；相同 Key 对应的文件内容或规范化后的 `name` 不同时返回 `ErrorCode.IDEMPOTENCY_KEY_CONFLICT (409)`。Key 与上传资源记录一同保留；MVP 不清理已引用资源或其异步任务审计记录，因此不设置独立过期时间。
- Request Body：

|  Param |  Type  |  Required  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  file | File | Yes | 上传的正式简历文件；仅允许 PDF |
|  name | String | No | 仅用于列表展示的文件名；服务端去除首尾空白后长度必须为 `1–255`。未提供或去除空白后为空时，服务端生成 `resume-{resume_id}.pdf`，不得作为内部对象定位 |

服务端必须校验扩展名、声明 MIME 类型和文件特征一致，并在写入正式对象前校验文件不超过 10 MB（10,000,000 bytes）；MVP 仅接受上传前已脱敏的简历，不提供脱敏确认、自动识别、自动脱敏或修复能力。成功响应仅表示受控文件对象、简历资源与 `AsyncTaskRun` 已原子创建，简历进入 `processing`；不得承诺解析已成功。

- Response：

```json
{
    "code":201,
    "msg":"上传已受理，正在解析简历",
    "data":{
        "resume_id":"resume_001",
        "parse_status":"processing"
    }
}
```

#### 获取简历列表

- 接口：GET /api/v1/resumes

- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  page | Integer | No | 页码，默认 `1`，最小 `1` |
  |  page_size | Integer | No | 每页数量，默认 `20`，范围 `1–100` |
- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "list":[
            {
                "resume_id":"resume_001",
                "name":"AI_Engineer_resume",
                "type":"resume",
                "parse_status":"succeeded",
                "created_at":"2026-07-18T09:00:00Z"
            }
        ],
        "total":1,
        "page":1,
        "page_size":20
    }
}
```

列表固定按 `created_at DESC, resume_id DESC` 排序，保证新上传简历优先且分页稳定。`created_at` 必须为 UTC RFC 3339 时间戳。`page` 或 `page_size` 不合法时返回 `ErrorCode.INVALID_REQUEST (400)`；`page` 超出总页数时返回 `200 / success`、空 `list` 以及实际的 `total`、请求的 `page` 和 `page_size`，不得返回 `404`。当 `parse_status` 为 `failed` 时，列表项额外返回 `failure_code`，其值仅可为 `parse_failure_code_enum` 中允许暴露的脱敏分类；其他状态不返回该字段。前端必须按下表基于 `failure_code` 展示固定文案，API 不返回 `failure_msg` 或自由文本错误。接口不得返回文件读取异常、解析器原始响应、堆栈或自由文本错误。

| `failure_code` | 固定用户提示 |
| --- | --- |
| `unsupported_file` | `文件格式不符合要求，请上传 PDF 简历` |
| `file_unreadable` | `文件无法解析，请上传可提取文本的 PDF` |
| `schema_validation_failed` | `未能提取必要的简历信息，请确认包含明确的目标岗位` |
| `parser_timeout` | `解析服务暂时不可用，请重新上传后再试` |
| `storage_unavailable` | `文件服务暂时不可用，请重新上传后再试` |
| `internal_error` | `解析暂时不可用，请重新上传后再试` |

该列表是 MVP 唯一的简历解析状态查看入口；客户端或开发者需要查看状态时可主动刷新列表。MVP 不提供单简历状态查询接口，也不提供轮询频率承诺、回调、Webhook、SSE、WebSocket 或广播通知。

### 求职者资料管理模块（`MVP`）

#### 上传求职者资料

- 版本：`MVP`

- 接口：POST /api/v1/candidate_documents
- Content-Type：`multipart/form-data`
- 请求头：复用正式简历上传的 `Idempotency-Key` 规则，包括 UUID 校验、同 Key 同请求重放首次 `201` 响应、不同请求 `409` 冲突及与资源记录同生命周期保留。
- Request Body：

|  Param |  Type  |  Required  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  file | File | Yes | 上传文件；仅允许 PDF、Markdown、JPG/JPEG |
|  candidate_document_type| String | Yes | 求职资料类型（证书/求职策略文档/其它，不包含简历）；仅可在候选人明确选择和授权后，由 Agent 发送的系统内消息作为附件引用 |
|  name | String | No | 仅用于列表展示的文件名；服务端去除首尾空白后长度必须为 `1–255`。未提供或去除空白后为空时，服务端按 `document-{candidate_document_id}.{extension}` 生成受控显示名 |

服务端必须校验扩展名、声明 MIME 类型和文件特征一致，并在写入正式对象前校验文件不超过 10 MB（10,000,000 bytes）。MVP 仅接受上传前已脱敏的候选人资料，不提供脱敏确认、自动识别、自动脱敏或修复能力。候选人资料无论文件格式均不进入异步解析，上传成功后仅可在候选人明确选择和授权后，由 Agent 发送的系统内消息作为附件引用。

- Response：

```json
{
    "code":201,
    "msg":"上传成功",
    "data":{
        "candidate_document_id":"doc_001"
    }
}
```

#### 获取求职者资料列表

- 版本：`MVP`

- 接口：GET /api/v1/candidate_documents

- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  page | Integer | No | 页码，默认 `1`，最小 `1` |
  |  page_size | Integer | No | 每页数量，默认 `20`，范围 `1–100` |
  |  candidate_document_type | String | No | 求职资料类型 |
- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "list":[
            {
                "candidate_document_id":"doc_001",
                "name":"bachelor's_degree_certificate",
                "type":"certificate",
                "created_at":"2026-07-18T09:00:00Z"
            }
        ],
        "total":1,
        "page":1,
        "page_size":20
    }
}
```

候选人资料列表固定按 `created_at DESC, candidate_document_id DESC` 排序；`created_at` 必须为 UTC RFC 3339 时间戳。`page` 或 `page_size` 不合法时返回 `ErrorCode.INVALID_REQUEST (400)`；`page` 超出总页数时返回 `200 / success`、空 `list` 以及实际的 `total`、请求的 `page` 和 `page_size`，不得返回 `404`。候选人资料为上传前已脱敏的原始附件，不包含 `parse_status`、`failure_code` 或解析结果。接口不得返回文件地址、文件正文或任何内部存储细节。

#### 获取指定简历的候选人画像

- 版本：`MVP`

- 接口：GET /api/v1/resumes/{resume_id}/profile
- Path Parameters：

  | Param | Type | Required | Description |
  | --- | --- | --- | --- |
  | resume_id | UUID | Yes | 当前候选人拥有的正式简历 ID |

- 语义：Agent 执行链路与候选人客户端可通过本接口确认指定简历是否已生成完整画像。服务端必须校验当前候选人对 `resume_id` 的归属；`parse_status = succeeded` 已保证画像在同一工作流中原子写入。解析中的简历不返回部分画像；画像生成、校验或写入失败按简历解析失败处理，不定义独立画像失败响应。简历不存在、不归属当前候选人或尚无可用画像时均返回安全 `404`。
- 响应 Schema：`target_job_titles` 为必填字符串数组；`skills`、`work_experience_summary` 与 `project_experience_summary` 始终返回数组，未知时返回 `[]`；`years_of_experience`、`education`、`expected_location` 与 `expected_salary` 未知时返回 `null`。不得省略这些字段或返回 Schema 未定义的字段。

  | 字段 | 类型 | 必填 | 说明 |
  | --- | --- | --- | --- |
  | `profile_id` | UUID | 是 | 画像 ID |
  | `resume_id` | UUID | 是 | 画像来源的简历 ID，必须与路径参数一致 |
  | `target_job_titles` | `string[]` | 是 | 从简历显式目标职位提取的至少一个非空字符串 |
  | `skills` | `Skill[]` | 是 | 技能列表；未知时为 `[]` |
  | `work_experience_summary` | `WorkExperience[]` | 是 | 工作经历摘要；未知时为 `[]` |
  | `project_experience_summary` | `ProjectExperience[]` | 是 | 项目经历摘要；未知时为 `[]` |
  | `years_of_experience` | `integer \| null` | 是 | 非负工作年限；未知时为 `null` |
  | `education` | `string \| null` | 是 | 学历；未知时为 `null` |
  | `expected_location` | `string \| null` | 是 | 期望地点；未知时为 `null` |
  | `expected_salary` | `string \| null` | 是 | 期望薪资；未知时为 `null` |

  `Skill = {name: string, proficiency: "beginner" | "intermediate" | "advanced" | "expert" | null}`。`WorkExperience = {company_name: string | null, title: string | null, start_date: string | null, end_date: string | null, summary: string | null, highlights: string[]}`，其中 `start_date` 与 `end_date` 必须为 `YYYY-MM`，未知时为 `null`。`ProjectExperience = {name: string, role: string | null, summary: string | null, technologies: string[], highlights: string[]}`。
- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "profile_id":"profile_001",
        "resume_id":"resume_001",
        "target_job_titles":["AI Agent Engineer"],
        "skills":[
            {"name":"Python","proficiency":"advanced"},
            {"name":"RAG","proficiency":null},
            {"name":"LangChain","proficiency":"intermediate"}
        ],
        "work_experience_summary":[
            {"company_name":"Example Co.","title":"AI Engineer","start_date":"2023-01","end_date":null,"summary":"...","highlights":["..."]}
        ],
        "project_experience_summary":[
            {"name":"Example Project","role":"Developer","summary":"...","technologies":["Python"],"highlights":["..."]}
        ],
        "years_of_experience":5,
        "education":null,
        "expected_location":null,
        "expected_salary":null
    }
}
```

### 岗位管理模块（`MVP`）

#### 创建岗位JD

- 接口：POST /api/v1/jobs
- Request Body
 ```json
{
    "title":"AI Agent Engineer",
    "company":"xxx",
    "jd_content":"xxx"
}
 ```
- Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "job_id":"job_001",
        "parse_status":"succeeded"
    }
}
 ```

#### 查询岗位列表
- 接口：GET /api/v1/jobs
- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  page | Integer | No | 页面 |
  |  keyword | IString | No | 岗位关键词 |
 - Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "list":[
            {
                "job_id":"job_001",
                "title":"AI Engineer",
                "company":"ABC",
                "location":"Guangzhou",
            }
        ],
        "total":20
    }
}
 ```

### 岗位匹配模块（`MVP`）

#### 查询可投递岗位

- 接口：GET /api/v1/matching/available-jobs
- Query Parmeters:

| Param                      | Type    | Required | Description    |
| -------------------------- | ------- | -------- | -------------- |
| goal_id                    | UUID    | Yes      | 求职目标       |
| page                       | Integer | No       | 页面           |
| page_size                  | Integer | No       | 每页数量       |
| exclude_application_status | String  | No       | 排除的申请状态 |

- Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "list":[
            {
                "job_id":"job_001",
                "job_title":"AI Engineer",
                "company":"ABC",
                "location":"Guangzhou",
                "salary":"20-35K"
            },
            {
                "job_id":"job_002",
                "job_title":"LLM Engineer",
                "company":"XYZ",
                "location":"Shenzhen",
                "salary":"25-40K"
            }
        ],
        "total":80
    }
}
 ```

#### 发起岗位匹配

- 接口：POST /api/v1/matching/tasks

- Request Body
 ```json
{
    "goal_id":"goal_001",
    "resume_id":"resume_001"
}
 ```


- Response：
 ```json
{
    "code":200,
    "msg":"匹配任务已启动",
    "data":{
        "task_id":"task_001",
        "status":"running"
    }
}
 ```

#### 获取匹配结果

- 接口：GET /api/v1/matching/results

- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  task_id | String | Yes | 匹配任务 |
  |  page | Integer | No | 页面 |

- Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "list":[
            {
                "job_id":"job_001",
                "title":"AI Engineer",
                "match_score":92,
                "skill_score":95,
                "gap":[
                    "Kubernetes"
                ],
                "recommend_reason":
                "技能高度匹配"
            }
        ]
    }
}
 ```

### 投递管理模块（`MVP`）

#### 创建岗位申请

- 接口：POST /api/v1/applications

- Request Body
 ```json
{
    "job_id":"job_001",
    "goal_id":"goal_001",
    "resume_id":"resume_001",
    "match_result_id":"match_001"
}
```

`goal_id` 为必填字段，是投递记录的归属锚点；`resume_id` 必须属于该求职目标的候选人。`match_result_id` 为可选字段，提供时必须属于同一候选人且对应同一岗位。


- Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "application_id":"app_001",
        "status":"created"
    }
}
 ```

#### 查询投递记录

- 接口：GET /api/v1/applications/{application_id}

- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  page | Integer | No | 页面 |
  |  status | String | No | 投递状态 |
- Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "list":[
            {
                "application_id":"app_001",
                "job_title":"AI Engineer",
                "company":"ABC",
                "status":"applied",
                "applied_at":"2026-07-18"
            }
        ]
    }
}
 ```

  ### AI求职沟通模块

#### 创建会话

- 接口：POST /api/v1/conversations

- Request Body
 ```json
{
    "application_id":"app_001"
}
 ```


- Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "conversation_id":"conv_001"
    }
}
 ```

#### 发送消息

- 接口：POST /api/v1/conversations/{conversation_id}/messages
- Request Body

 ```json
{
    "content":"这是一条测试文本",
    "candidate_document_ids":["doc_001"]
}
 ```

`candidate_document_ids` 为可选数组。每一项必须属于当前候选人、资料对象存在，且候选人与该会话所属投递记录一致；候选人必须在本次发送中明确选择并授权资料。Agent 可据此创建系统内候选人消息和附件引用，但不得自行上传、选择或读取资料正文；系统不向真实 HR 或外部平台发送。MVP 中，Agent 仅可使用完成授权所需的最小附件元数据，资料正文不自动进入 Agent/LLM 输入。

- Response：

 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "message_id":"msg_001",
        "reply":"这是一条测试文本",
        "attachment_ids":["attachment_001"]
    }
}
 ```

#### 获取聊天记录

- 接口：GET /api/v1/conversations/{conversation_id}/messages

- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  page | Integer | No | 页面 |

- Response 中每条消息应返回其附件引用的最小信息：`attachment_id`、`candidate_document_id`、`name`、`file_type`；不得返回文件地址、文件正文或内部存储细节。

### 求职进度管理模块（`MVP`）

#### 查询求职进度

- 接口：GET /api/v1/applications/{application_id}/progress
- Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "events":[
            {
                "from_stage":"screening",
                "to_stage":"interview_1",
                "created_at":
                "2026-07-18"
            }
        ]
    }
}
 ```

#### 更新求职进度

- 接口：POST /api/v1/applications/{application_id}/events

- Request Body：
 ```json
{
    "to_stage":"interview_2",
}
 ```

- Response：
 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "event_id":"event_001",
        "to_stage":"interview_2",
    }
}
 ```
