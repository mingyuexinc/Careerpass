# 切片：用户登录技术设计

> 本文档只记录用户登录 Slice 的技术落地事实和验证证据。
>
> 业务目标、输入、输出、前置条件、业务规则、范围和验收标准以同目录的 [`slice-spec.md`](slice-spec.md) 为准。跨 Slice 的领域、数据库和业务事实以对应全局事实源为准。

## 1. 文档职责与事实源

### 1.1 当前 Slice 的技术事实

- API、异步任务和 Handoff Contract：本文档；
- 跨前后端业务事实：[`business-baseline.md`](../../../../../docs/business/business-baseline.md)；本 Slice 使用 `BF-FLOW-002`、`BF-RULE-001`、`BF-RULE-002`、`BF-RULE-003` 和 `BF-RULE-009`；
- 领域模型：[`domain-model.md`](../../../domain/domain-model.md)；
- 数据库设计：[`database-design.md`](../../../data/database-design.md)；
- 跨 Slice 业务规则：[`business-rules.md`](../../../product/business-rules.md)；
- 后端架构：[`backend-architecture.md`](../../../architecture/backend-architecture.md)；
- 代码分层、统一响应和安全规则：[`backend-guidelines.md`](../../backend-guidelines.md)；
- 当前实现证据：`careerpass-backend/app/`、Alembic 迁移和 `careerpass-backend/tests/`。

### 1.2 维护规则

- API、身份交接、数据影响和关键依赖在 Slice Design 阶段锁定；
- Implement 阶段只补充与已确认设计一致的实现方案和局部决策；
- Verify、Close 阶段补充验证证据和最终一致性结论；
- 业务范围、用户可观察结果、权限语义、状态语义或已锁定契约发生变化时，回退到 Slice Design；
- 本文档不复制完整领域模型、数据库设计或全局业务规则。

## 2. API、异步任务与交接契约

### 2.1 接口契约：用户登录

#### `POST /api/v1/auth/login`

- 调用方：登录页和前端认证流程；
- 输入：用户名、密码和可选的当前工作区身份；
- 用户名：去除首尾空白后，长度 3–64，仅允许字母、数字、下划线、点和连字符；
- 密码：长度 1–128，作为敏感值处理，不写入日志、追踪或响应；
- 当前工作区身份：可选的 `candidate` 或 `hr`；服务端必须确认该身份属于当前用户；多身份用户未指定时不得自动猜测；
- 成功状态：HTTP 200；
- 成功响应：统一 `{code, msg, data}` 结构，`data` 包含短期 `access_token`、`token_type`、`expires_in` 和最小身份信息；
- 身份信息：`user_id`、`roles`、`active_role`、可选的 `candidate_id`、`hr_profile_id` 和 `profile_status`；登录成功时 `profile_status` 当前不参与身份确认，保持为 `null`；
- 失败状态：
  - 请求格式或字段校验失败：HTTP 400，统一校验错误；
  - 用户不存在、密码错误、工作区身份未授权或业务身份关联不一致：HTTP 401，统一 `invalid credentials`；
- 幂等与副作用：重复登录不创建或修改用户、业务身份及业务资源；每次成功登录可以签发新的短期令牌；不触发异步任务、LLM 调用或外部请求。

成功响应的结构示例：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "access_token": "<短期 JWT>",
    "token_type": "Bearer",
    "expires_in": 1800,
    "user": {
      "user_id": "<uuid>",
      "roles": ["candidate"],
      "active_role": "candidate",
      "candidate_id": "<uuid-or-null>",
      "hr_profile_id": null,
      "profile_status": null
    }
  }
}
```

`expires_in` 由运行配置决定，示例值不构成固定配置。

### 2.2 接口契约：当前身份恢复

#### `GET /api/v1/auth/me`

- 调用方：已登录前端和后续受保护请求；
- 输入：`Authorization: Bearer <access_token>`；
- 服务端处理：验证令牌，并重新从持久化身份关系中解析当前用户和工作区身份；
- 成功状态：HTTP 200；
- 成功响应：统一 `{code, msg, data}` 结构，`data` 包含 `user_id`、`username`、`name`、`roles`、`active_role`、可选业务身份 ID 和 `profile_status`；
- 失败状态：缺失、无效、过期或无法重新确认身份关系的令牌返回 HTTP 401，错误语义为 `authentication failed`；
- 业务边界：该接口只恢复认证身份，不替代后续业务资源的归属和权限校验。

### 2.3 异步任务契约

本 Slice 不产生异步任务，不使用 Dispatcher、Celery、Redis 任务队列或外部 Agent 能力。

### 2.4 交接契约：认证身份交接

| 项目 | 约定 |
| --- | --- |
| Contract ID / 版本 | `S-01-authenticated-identity` / `v1` |
| Producer | S-01 用户登录 |
| Consumer | 后续需要认证身份的资料、解析、岗位、求职目标、匹配、投递和沟通 Slice |
| 触发条件 | 登录成功并签发短期令牌，或受保护请求成功恢复当前身份 |
| 输出 | `access_token`、`user_id`、`roles`、`active_role` 以及服务端已确认的可选 `candidate_id`、`hr_profile_id` |
| 身份关系 | `User`、`UserRole` 和所选 `Candidate`/`HrProfile` 必须能由服务端持久化数据重新确认 |
| 资源授权 | `active_role` 只表示当前工作区，不等同于具体业务资源访问许可 |
| 幂等 | 重复登录不创建用户、业务身份或业务资源；每次成功登录可签发新的短期令牌 |
| 失败交接 | 认证失败不触发下游 Slice；下游请求必须重新解析当前身份 |

Consumer 只引用 `S-01-authenticated-identity/v1`，不得复制或重新定义该交接契约。

## 3. 领域实体与数据影响

### 3.1 实体使用

| 实体 | 本 Slice 用途 | 读写变化 | 归属/授权 | 全局事实源 | 处理结果 |
| --- | --- | --- | --- | --- | --- |
| `User` | 查询认证主体、校验凭证和账号身份 | 查询；登录不创建或修改 | 认证主体 | [`domain-model.md`](../../../domain/domain-model.md) | 已确认，无本 Slice 新增变化 |
| `Candidate` | 为求职者工作区提供业务身份 | 查询；登录不创建或修改 | 一对一归属于 `User` | [`domain-model.md`](../../../domain/domain-model.md) | 已确认，无本 Slice 新增变化 |
| `HrProfile` | 为 HR 工作区提供业务身份 | 查询；登录不创建或修改 | 一对一归属于 `User` | [`domain-model.md`](../../../domain/domain-model.md) | 已确认，无本 Slice 新增变化 |
| `UserRole` | 确认用户是否拥有目标工作区身份 | 查询；前端不能直接写入 | 关联 `User` 与可用工作区身份 | [`domain-model.md`](../../../domain/domain-model.md) | 已确认，无本 Slice 新增变化 |
| `CurrentIdentity` | 为受保护请求提供可信当前身份上下文 | 运行时构造；不持久化 | 来源于已确认的用户、角色和业务身份关系 | [`domain-model.md`](../../../domain/domain-model.md) | 已确认，为运行时投影 |

所有身份数据访问通过 Repository 完成。认证依赖在令牌解析后重新查询并校验用户、角色和业务身份关系，不能仅凭令牌中的用户标识或前端提交的工作区身份形成授权事实。

### 3.2 数据库影响

- 新增或修改的表、字段、关系、约束和索引：无；
- Alembic 迁移：无本 Slice 新增迁移；身份基础结构由 `20260725_0002_auth_user_candidate` 和 `20260811_0005_auth_roles_and_hr_profiles` 提供；
- 事务边界：登录只读取已提交的身份数据；不产生业务资源写入事务；
- 数据库事实源：[`database-design.md`](../../../data/database-design.md)；
- 本 Slice 不重复定义表字段，因为没有新增数据结构，且现有表结构已在全局数据库设计中登记。

### 3.3 状态与业务规则同步

- 本 Slice 不改变业务资源状态，也不新增状态迁移；
- `CurrentIdentity` 是认证上下文投影，不是持久化实体；
- 资源归属和授权规则引用 [`business-rules.md`](../../../product/business-rules.md) 及领域模型，不在登录 Slice 内提前定义具体资源权限；
- `HrProfile`、`UserRole` 和 `CurrentIdentity` 的稳定含义已同步到 [`domain-model.md`](../../../domain/domain-model.md)。

## 4. 技术实现方案

### 4.1 用户登录调用链

```text
POST /api/v1/auth/login
  → LoginRequest 结构校验
  → LoginService 编排认证用例
  → UserRepository 按用户名查询
  → 校验密码摘要
  → IdentityRepository 查询角色和 Candidate/HrProfile
  → 服务端确认 active_role
  → 签发短期 Access Token
  → 统一成功响应
```

### 4.2 当前身份恢复调用链

```text
GET /api/v1/auth/me 或其他受保护请求
  → 解析 Bearer Access Token
  → 提取用户标识和 active_role 上下文
  → IdentityRepository 重新查询用户、角色和业务身份
  → 构造 CurrentIdentity
  → 交给受保护业务 Slice
```

### 4.3 分层边界

- API 层负责请求解析、认证异常映射和统一响应封装；
- Service 层负责登录用例编排，不直接访问 ORM Session；
- Repository 层负责用户、角色和业务身份关系查询；
- 认证依赖负责令牌校验和当前身份恢复；
- `CurrentIdentity` 作为运行时身份投影传入后续业务代码；
- 注册接口属于现有认证基础设施，不属于本 Slice 的登录业务契约，本技术设计不扩展其业务范围。

### 4.4 局部实现决策

| 决策 | 选择 | 简短理由 |
| --- | --- | --- |
| 多身份用户未指定工作区身份 | 不自动选择，要求明确身份 | 避免把登录上下文错误地解释为用户意图 |
| 登录和身份恢复的错误 | 使用统一认证失败语义 | 防止暴露账号、密码和身份关联细节 |
| 当前身份的业务身份字段 | 在运行时投影中保留可选 `candidate_id` 和 `hr_profile_id` | 复用现有身份模型，支持后续 Slice 按当前工作区继续校验归属 |

## 5. 外部依赖、失败处理与安全边界

### 5.1 依赖与证据

| 依赖 | 用途 | 真实证据 | 状态 |
| --- | --- | --- | --- |
| PostgreSQL | 读取用户、角色和业务身份关系 | 已有 Alembic 迁移、Repository 测试和运行时集成测试 | 已确认 |
| 短期 Access Token 机制 | 登录成功后的认证交接 | 认证单元测试、API 测试和当前身份依赖测试 | 已确认 |
| 前端真实认证流程 | 登录和工作区进入 | 已完成前后端联调，结果正常 | 已确认 |

本 Slice 不依赖 Redis、Celery、LLM、对象存储或其他外部服务。

### 5.2 失败处理

- 输入校验失败：返回统一校验错误，不进入凭证校验；
- 用户不存在、密码错误或身份关联异常：返回统一 `invalid credentials`，不区分具体原因；
- 令牌缺失、无效、过期或身份关系无法复核：返回统一 `authentication failed`；
- 身份查询失败：不返回内部异常、数据库信息或路径；
- 登录失败不写入业务资源，不触发下游 Slice；
- 登录不产生异步任务，因此不适用任务重试和终态规则。

### 5.3 敏感信息

- 密码原值、密码摘要和令牌不得进入普通日志、追踪或非必要响应；
- Access Token 只返回给登录调用方，用于后续认证请求，不写入诊断日志；
- 错误响应不得包含账号是否存在、身份关联细节、数据库信息、内部路径或异常堆栈；
- 诊断只保留请求 ID、处理阶段、结果和必要耗时等最小脱敏信息。

## 6. 实现决策记录

### 6.1 开发者需裁决事项

None. 用户登录 Slice 已完成范围、身份语义、接口行为和技术方向裁决。

### 6.2 设计变化与回退

本 Slice 实施过程中未发现需要回退的产品范围、契约、数据或架构变化。已确认的 `HrProfile`、`UserRole` 和 `CurrentIdentity` 领域含义已同步到全局领域模型。

## 7. 验证结果与关闭结论

### 7.1 验证证据

| 验证类型 | 覆盖内容 | 结果 | 证据 |
| --- | --- | --- | --- |
| Schema | 用户名格式、密码长度、工作区身份枚举和敏感值承载 | 通过 | `tests/unit/test_auth_schemas.py` |
| Service | 正确凭证、未知用户、错误密码、缺失或不匹配身份 | 通过 | `tests/unit/test_login_service.py` |
| 身份解析 | 有效令牌、角色选择、用户/角色/业务身份关系复核和无效令牌 | 通过 | `tests/unit/test_current_identity.py`、`tests/unit/test_identity_context_repository.py` |
| API | 统一响应、登录失败、`/auth/me` 和敏感信息边界 | 通过 | `tests/integration/test_application.py` |
| 数据访问 | 用户、角色、Candidate 和 HR 身份关系访问 | 通过 | `tests/unit/test_identity_repositories.py`、`tests/unit/test_demo_account_repository.py` |
| 前后端联调 | 求职者和 HR 登录、身份恢复、失败反馈和工作区进入 | 通过 | 开发者已完成真实前后端联调，结果正常 |

### 7.2 关闭结论

- `slice-spec.md` 与最终业务范围一致：是；
- 本文档与代码、迁移和测试一致：是；
- 全局领域、数据和业务事实已同步：是；
- Handoff Contract 可供下游使用：是，使用 `S-01-authenticated-identity/v1`；
- 未决开发者裁决：无；
- 最终结论：**Slice Done**。
