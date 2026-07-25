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
|  content-Type | Yes | application/json | 
|  Authorization| 除认证公开接口外均必填 | Bearer {access_token}；`/api/v1/auth/register`、`/api/v1/auth/login`、`/api/v1/auth/refresh` 无需此请求头 |
|  X-Request-ID | No | 请求追踪ID | 


### 统一响应格式

|  Field |  Type  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  code | Integer | 业务状态码 | 
|  msg | String | 状态描述 |
|  data | T | 业务数据 | 

- 示例：
```
json
{
	"code":200,
	"msg":"success",
	"data"：{}
}
```


### 分页响应

```
json
{
	"code":200,
	"msg":"success",
	"data"：{
		"list":[].
		"total":100,
		"page":1,
		"size":20
	}
}
```

### 错误码范围

|  Range |  Category | 
|- - - - |- - - - -|
|  200 | 成功 |
|  400 | 参数错误 | 
|  401 | 未认证 |
|  403 | 无权限 |
|  404 | 资源不存在 |
|  409 | 业务冲突 |
|  500 | 服务端错误 |

### 版本适用范围

| 标记 | 含义 |
| --- | --- |
| `MVP` | 当前 MVP 必须实现、测试并纳入验收的接口能力。 |
| `Deferred` | 已完成设计但不属于当前 MVP 实现范围的后续能力；不得作为 MVP 开发依赖或验收条件。 |

未单独标记的既有接口，适用范围以所属模块或其所在章节的标记为准。范围裁决以 `.harness/wiki/MVP scope and development boundaries.md` 为最高依据。

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
            "candidate_id":"candidate_001",
            "profile_status":"incomplete"
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
            "candidate_id":"candidate_001",
            "profile_status":"ready"
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
        "name":"Alice",
        "profile_status":"ready"
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

- 接口：POST /api/v1/resume/upload
- Request Body：

|  Param |  Type  |  Required  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  resume | File | Yes | 上传文件 |
|  type| String | Yes | 文件类型 |
|  name | String | No | 文件名称 |

- Response：

```json
{
    "code":200,
    "msg":"upload success",
    "data":{
        "resume_id":"resume_001",
        "parse_status":"processing"
    }
}
```

#### 获取简历列表

- 接口：GET /api/v1/resume

- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  page | Integer | No | 页面，默认1 |
  |  page_size | Integer | No | 每页数量 |
  |  type| String | Yes | 文件类型 |
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
                "created_at":"2026-07-18"
            }
        ],
        "total":1
    }
}
```

### 求职者资料管理模块（`MVP` 与 `Deferred`）

#### 上传求职者资料

- 版本：`Deferred`

- 接口：POST /api/v1/candidate_documents/upload
- Request Body：

|  Param |  Type  |  Required  |  Description  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  file | File | Yes | 上传文件 |
|  candidate_document_type| String | Yes | 求职资料类型（证书/求职策略文档/其它，不包含简历） |
|  name | String | No | 文件名称 |

- Response：

```json
{
    "code":200,
    "msg":"upload success",
    "data":{
        "candidate_document_id":"doc_001",
        "parse_status":"processing"
    }
}
```

#### 获取求职者资料列表

- 版本：`Deferred`

- 接口：GET /api/v1/candidate_documents

- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  page | Integer | No | 页面，默认1 |
  |  page_size | Integer | No | 每页数量 |
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
                "parse_status":"succeeded",
                "created_at":"2026-07-18"
            }
        ],
        "total":1
    }
}
```

#### 获取候选人画像

- 版本：`MVP`

- 接口：GET /api/v1/profile
- Response：

```json
{
    "code":200,
    "msg":"success",
    "data":{
        "profile_id":"profile_001",
        "target_job_titles":"AI Agent Engineer",
        "skills":[
            "Python",
            "RAG",
            "LangChain"
        ],
        "years_of_experience":5
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
    "msg":"matching started",
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
    "content":
    "这是一条测试文本"
}
 ```

- Response：

 ```json
{
    "code":200,
    "msg":"success",
    "data":{
        "message_id":"msg_001",
        "reply":
        "这是一条测试文本"
    }
}
 ```

#### 获取聊天记录

- 接口：GET /api/v1/conversations/{conversation_id}/messages

- Query Parameters：

  |  Param |  Type  |  Required  |  Description  |
  |- - - - |- - - - -| - - - - - -  - - -| 
  |  page | Integer | No | 页面 |

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
