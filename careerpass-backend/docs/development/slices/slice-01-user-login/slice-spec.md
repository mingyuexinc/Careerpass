# Slice 01：用户登录

> 当前阶段：关闭（Close）
>
> 当前状态：passed

## 1. 目标与范围

### 1.1 目标

用户提交账号和密码后，系统完成凭证校验，返回短期 Access Token 和最小可信身份；后续请求可以据此解析当前用户，并进入与身份匹配的工作区。

### 1.2 本次实现范围

- 支持受控用户使用用户名和密码登录。
- 校验用户名、密码以及用户选择的已授权角色身份。
- 返回统一响应结构 `{code, msg, data}`，成功数据只包含后续流程所需的最小身份信息。
- 支持受保护请求通过 `GET /api/v1/auth/me` 读取当前身份。
- 明确未登录、凭证错误、无效令牌和身份归属不一致的失败结果。
- 为后续简历、资料、求职目标和岗位流程提供稳定的身份交接点。

### 1.3 不在本切片范围

- 用户注册页面和注册产品流程；当前版本使用版本范围文档定义的受控演示账号初始化，不将初始化流程视为注册能力。
- 用户退出；当前版本由前端本地清理身份，后端不提供退出接口。
- Refresh Token、服务端会话、Token 轮换、设备管理、第三方登录、多租户账号体系。
- 具体业务资源的授权与归属校验；该能力按版本范围延期，由后续范围变更或切片另行裁决。
- 任何简历、岗位、投递、沟通或 Agent 业务行为。

## 2. 触发条件与完成结果

| 项目 | 定义 |
| --- | --- |
| 触发条件 | 用户在登录页选择身份并提交用户名、密码 |
| 核心业务结果 | 返回认证结果和最小可信当前身份 |
| 成功后的可观察结果 | 前端保存当前身份，进入与服务端身份一致的业务工作区；调用 `/auth/me` 可恢复该身份 |
| 失败后的可观察结果 | 返回面向用户的认证失败；不创建或修改业务资源，不暴露账号是否存在、密码校验细节或内部异常 |
| 稳定交接点 | `Authorization: Bearer <access_token>` 可供后续切片的认证依赖解析 `CurrentIdentity` |

登录本身不产生异步任务、LLM 调用、外部请求或不可逆副作用。

## 3. 前置条件与上下游衔接

### 3.1 前置条件

- 服务启动前数据库必须完成 Alembic 迁移；应用启动时自动幂等初始化两个受控演示 User：`candidate_01`（Candidate）和 `hr_01`（HrProfile）。
- 演示账号密码由版本范围文档定义，仅用于受控环境初始化和登录验证，不进入 API 响应、日志或追踪。
- 角色身份由服务端维护；前端提交的角色只是登录上下文提示，不能单独形成后端事实。
- User 保存用户名和密码哈希；密码原值不进入数据库、日志、追踪或响应。
- Access Token 的签发、解析和过期配置已由当前认证基础设施提供。
- API 使用统一响应封装和认证异常映射。

### 3.2 上游输入

登录页来自正式前端的公共 F-01 流程：用户选择求职者或 HR 身份，输入预置账号和密码并提交。服务端根据 User 的角色关联校验所选身份，前端通过真实登录 API 获取服务端身份结果。

### 3.3 下游输出

后续切片依赖认证上下文中的 `user_id`、角色集合、`active_role` 以及对应的业务身份 ID。角色身份只说明用户以何种身份进入工作区，不自动代表对具体业务资源拥有访问权；具体资源授权不在本版本登录切片中裁决。

### 3.4 身份模型裁决

- `User` 是统一认证主体，负责用户名、密码哈希和账户状态。
- `Candidate` 与 `HrProfile` 是挂载在 User 上的业务身份；二者可以分别存在，是否允许同一 User 同时拥有两种身份由账户配置决定。
- `UserRole`（或等价的角色关联）记录 User 可使用的 `candidate` / `hr` 角色。
- 登录请求中的角色是 `active_role` 候选值；服务端必须校验该角色属于当前 User。
- `CurrentIdentity` 不再固定要求 `candidate_id`，应表达 `user_id`、`roles`、`active_role`、可选的 `candidate_id` 和 `hr_profile_id`。

该裁决解决了 S-01 的身份阻塞；HR 的具体岗位资源授权仍不属于登录切片。

## 4. 现状与影响分析

### 4.1 已有证据

| 能力 | 当前证据 | 判断 |
| --- | --- | --- |
| 登录请求校验 | `LoginRequest` 校验用户名格式、长度和密码长度 | 可复用 |
| 凭证校验与令牌签发 | `LoginService` 通过 `UserRepository` 查询、校验密码并签发短期 Access Token | 可复用 |
| Candidate 业务身份 | 当前迁移和 Repository 已确认 `User → Candidate` 一对一关系 | 可复用 |
| 当前身份解析 | `GET /api/v1/auth/me` 使用认证依赖解析 `CurrentIdentity` | 可复用 |
| User/Candidate 数据结构 | 当前迁移和领域文档已确认 User、Candidate 及唯一归属关系 | 可复用 |
| 前端真实后端接入 | 前端已接入真实认证 API，并完成前后端联调测试 | 已完成 |
| HR 业务身份 | 本切片已落地 `User → HrProfile` 与角色关联模型、迁移和解析 | 已实现 |

### 4.2 影响边界

本切片锁定统一认证主体和角色身份上下文，不提前锁定 HR 岗位、候选人投递或沟通模型。后续切片需要在自身契约中裁决具体资源的授权和归属；不得把登录角色直接当作资源访问许可。

## 5. 领域实体确认与领域模型影响

本切片涉及的领域对象如下：

| 对象 | 类型 | 本切片用途 | 查询/写入方式 | 归属关系 | 来源证据 | 处理 |
| --- | --- | --- | --- | --- | --- | --- |
| `User` | 持久化实体 | 查询认证主体、校验凭证和账户状态 | `UserRepository` 查询；不创建或修改 | 认证主体 | 当前代码、迁移、Repository 和测试 | 已确认 |
| `Candidate` | 持久化实体 | 查询候选人业务身份并生成身份上下文 | `CandidateRepository` 查询；登录时不创建或修改 | 一对一归属于 `User` | 当前代码、迁移和登录实现 | 已确认 |
| `HrProfile` | 持久化实体 | 查询 HR 业务身份并生成身份上下文 | `IdentityRepository` 查询；登录时不创建或修改 | 归属于 `User` | 当前代码、迁移和本切片设计 | 已确认 |
| `UserRole` | 关联实体 | 校验用户是否拥有请求的 `active_role` | `IdentityRepository` 查询；不直接由前端写入 | 关联 `User` 与可用业务身份 | 当前代码、迁移和角色校验实现 | 已确认 |
| `CurrentIdentity` | 运行时投影/值对象 | 为受保护请求提供当前用户、角色和业务身份上下文 | 认证依赖解析 Token，并由 Repository 复核 | 来源于 `User`、`UserRole`、`Candidate` 和 `HrProfile` | 当前认证依赖、身份测试和本切片设计 | 已确认，不持久化 |

本切片只查询已有身份数据，不创建 `User`、`Candidate`、`HrProfile` 或业务资源；重复登录只允许签发新的短期 Token，不得产生重复实体。

所有身份查询必须通过 Repository 完成，并沿 `User → UserRole → Candidate/HrProfile` 关系复核归属。前端提交的角色只能作为登录上下文候选值，不能直接创建或授权后端角色。

本切片确认的 `HrProfile`、`UserRole` 和 `CurrentIdentity` 已同步到 [`domain-model.md`](../../../domain/domain-model.md)；其中 `CurrentIdentity` 被定义为认证上下文投影，不作为持久化实体。

## 6. 接口与数据契约

本节是本切片实际使用的 API 契约事实源。

### 6.1 登录

`POST /api/v1/auth/login`

请求：

```json
{
  "username": "controlled-user",
  "password": "<secret>",
  "active_role": "candidate"
}
```

约束：

- `username` 去除首尾空白，长度 3–64，只允许字母、数字、下划线、点和连字符。
- `password` 长度 1–128；使用 Secret 类型承载，不在日志或异常中输出。
- `active_role` 可选值为 `candidate` 或 `hr`，表示本次工作区上下文。
- 服务端必须校验该角色属于登录 User；未提供时，仅当 User 只有一个可用角色时才能自动选择。
- 前端提交的角色不是后端事实，不能将未关联到该 User 的角色写入 Token 或响应。

成功响应（HTTP 200）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "access_token": "<opaque-jwt>",
    "token_type": "Bearer",
    "expires_in": 1800,
    "user": {
      "user_id": "<uuid>",
      "roles": ["candidate"],
      "active_role": "candidate",
      "candidate_id": "<uuid-or-null>",
      "hr_profile_id": null
    }
  }
}
```

`expires_in` 的具体值由运行配置决定；示例值不构成固定配置。响应不得返回密码、密码哈希、存储位置、原始异常或模型信息。

失败：

| 场景 | HTTP | `code` / `msg` | 规则 |
| --- | --- | --- | --- |
| 请求格式或字段校验失败 | 422 | 统一校验错误 | 不进入凭证校验，不暴露敏感值 |
| 用户不存在、密码错误、角色未关联或业务身份关联不一致 | 401 | `UNAUTHORIZED` / `invalid credentials` | 对外使用同一失败语义 |

### 6.2 当前身份

`GET /api/v1/auth/me`

请求头：

```text
Authorization: Bearer <access_token>
```

成功响应（HTTP 200）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "user_id": "<uuid>",
    "username": "controlled-user",
    "name": "<controlled-name-or-null>",
    "roles": ["candidate"],
    "active_role": "candidate",
    "candidate_id": "<uuid-or-null>",
    "hr_profile_id": null
  }
}
```

无效、过期、缺失或无法复核 User/角色身份的令牌返回统一未授权错误。该接口只恢复认证身份，不替代后续业务资源授权。

### 6.3 交接契约（Handoff Contract）

| 项目 | 约定 |
| --- | --- |
| Producer | S-01 用户登录 |
| 消费者 | 后续需要身份的资料、解析、求职目标和岗位切片 |
| 触发条件 | 登录成功并签发短期 Access Token |
| 输入 | 已通过校验的账号凭证 |
| 输出 | `access_token`、`user_id`、`roles`、`active_role` 以及对应的可选业务身份 ID |
| 身份关系 | User、角色关联和 Candidate/HrProfile 身份必须能由服务端数据访问层复核 |
| 幂等 | 重复登录不创建 User、Candidate 或业务资源；每次成功登录可签发新的短期 Token |
| 失败交接 | 凭证、角色或身份关联校验失败不产生下游触发；后续切片必须重新解析当前身份 |

`active_role` 是已锁定的登录上下文输出，但不等同于具体业务资源授权。

## 7. 技术方案

```text
POST /auth/login
  → LoginRequest 结构化校验
  → LoginService
  → UserRepository 按 username 查询
  → verify_password
  → IdentityRepository 查询可用角色和业务身份
  → create_access_token
  → success_response

后续受保护请求
  → Bearer Token 解析
  → CurrentIdentity 认证依赖
  → Repository 复核 User、角色和业务身份关联
  → 业务切片按自身契约处理业务资源
```

- Service 只编排认证用例，不直接访问 ORM Session 或编写 SQL。
- Repository 负责 User、角色关联和 Candidate/HrProfile 身份数据访问；不在 Service 中直接访问 ORM Session。
- 认证错误统一映射为安全的失败语义，日志只保留关联 ID、阶段、结果和耗时等最小诊断信息。
- 本切片不引入异步任务、缓存、Agent 工作流或外部能力。

## 8. 就绪检查（Readiness Check）

| 检查项 | 结果 | 证据或阻塞 |
| --- | --- | --- |
| 单一业务结果和闭环 | 通过 | 登录成功后得到可信身份并可调用 `/auth/me` |
| 前端触发和可观察结果 | 通过 | 前端登录页已接入真实认证 API，前后端联调测试结果正常 |
| 候选人认证契约 | 通过 | 当前 Schema、API、Service、Repository、迁移和测试已存在 |
| HR 角色契约 | 通过 | 已确定统一 User、角色关联和 `HrProfile` 业务身份；具体岗位授权不属于本切片 |
| 全局领域模型同步 | 通过 | `HrProfile`、`UserRole` 和 `CurrentIdentity` 已补充到 [`domain-model.md`](../../../domain/domain-model.md) |
| 统一响应和敏感字段边界 | 通过 | 认证响应统一封装，令牌/密码边界已有实现约束 |
| 后续身份交接 | 通过 | Candidate 与 HR 均通过 `User + active_role + 业务身份 ID` 交接 |
| 验证结论 | 通过 | 自动化测试和前后端联调测试均已完成，结果正常 |

## 9. 实现范围

- [x] 建立 User 与 Candidate/HrProfile 的身份关联及角色关联数据访问。
- [x] 增加幂等演示账号初始化，预置 `candidate_01` 和 `hr_01` 及对应业务身份。
- [x] 实现登录请求的 `active_role` 校验和统一身份响应。
- [x] 保持或补齐登录、`/auth/me`、无效凭证、无效令牌和身份归属不一致测试。
- [x] 完成前端从模拟登录到真实认证 API 的适配，并按服务端身份进入对应工作区。
- [x] 将已确认的 `HrProfile`、`UserRole` 和 `CurrentIdentity` 领域含义同步到领域模型文档。
- [x] 完成用户登录前后端联调测试，验证真实认证 API、身份恢复和失败反馈；测试结果正常。

## 10. 验证与关闭（Verify、Close）

### 10.1 验证要求

- Schema：用户名、密码、非法字符、空值和长度边界。
- Service：两个预置账号成功登录、未知用户、错误密码、角色未关联、缺失业务身份和 User/身份不一致。
- API：成功响应统一结构、401 失败语义、`/auth/me` 的 Bearer 校验和敏感字段不泄露。
- 集成：初始化后的 User、角色关联和 Candidate/HrProfile 使用真实 Repository 完成双角色登录并恢复当前身份；初始化重复执行保持幂等。
- 前后端端到端验收：求职者和 HR 登录、角色隔离、失败反馈、重复提交保护和退出后的登录页回退。

### 10.2 完成标准（Definition of Done）

- User 统一认证主体、Candidate/HrProfile 业务身份和角色关联已形成可审计契约。
- 登录和当前身份 API 的请求、响应、错误和敏感字段边界已锁定。
- Candidate 与 HR 的角色一致性由后端校验，不依赖前端传入或模拟状态。
- `CurrentIdentity` 能恢复 User、角色和对应业务身份；具体资源授权由后续业务切片另行裁决。
- 后端测试和真实前端端到端验收通过，且不产生真实外部副作用。
- 文档与最终实现一致，未把注册、退出、Refresh Token 或下游业务能力混入本切片。

### 10.3 关闭结论（Close）

当前结论：**切片完成（Slice Done）**。统一 User 认证主体、Candidate/HrProfile 业务身份、角色关联、预置账号和真实前端登录已实现；自动化测试及前后端联调测试均已完成，结果正常。`HrProfile`、`UserRole` 和 `CurrentIdentity` 的领域模型已同步，文档与最终实现一致。
