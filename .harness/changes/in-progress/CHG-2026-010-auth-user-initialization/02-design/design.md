# 认证与用户初始化方案设计

> 阶段：3（方案设计）
> 依据：`01-analysis/requirements.md`、`01-analysis/impact-analysis.md`、`02-prevalidation/postgresql-prevalidation.md`
> 设计状态：已按开发者裁决通过

## 1. 方案目标与设计裁决

本方案只支持受控 Demo 的最小认证闭环：注册、登录、当前身份解析和 `/auth/me`。注册必须在真实 PostgreSQL 中原子创建 `User + Candidate`；登录和受保护请求必须重新从数据库复核候选人归属。

已确认的技术路线：

- Web 层采用 FastAPI，输入输出采用 Pydantic 2 契约。
- 凭据采用 Python 标准库 `scrypt` 哈希；密码明文只在请求处理期间存在。
- Access Token 采用 HS256 JWT，包含最小身份声明，并校验签发方、受众和有效期。
- 持久化采用 SQLAlchemy 2.0 + Repository + Alembic + PostgreSQL 16。
- 统一响应固定为 `{code, msg, data}`。
- Redis 认证限流不属于当前模块；认证路由、配置和测试不得直接依赖 Redis。项目其他变更包对 Redis 的使用由其自身门禁管理。

## 2. 模块边界与分层

| 层级 | 本模块职责 | 明确不拥有 |
| --- | --- | --- |
| API Router | 解析请求、注入 Service/当前身份、转换统一响应 | ORM Session、SQL、密码哈希、JWT 解析、客户端传入的身份 ID |
| Pydantic Schema | 校验用户名、密码、姓名，限制响应字段 | 数据库唯一性判断、凭据验证、业务授权 |
| Registration/Login Service | 编排哈希、Repository 调用、Token 签发和安全错误语义 | SQL、Session、跨候选人资源访问 |
| Current Identity Dependency | 校验 Bearer JWT，并从 Repository 复核 User/Candidate 关联 | 信任 Token 中的 candidate_id、从请求体读取当前用户 |
| User/Candidate Repository | 独占 User/Candidate 查询及原子创建 | API 响应格式、JWT、密码策略 |
| PostgreSQL/Alembic | 持久化约束、外键、唯一性和时间字段 | 认证业务错误文案、HTTP 状态码 |

依赖方向固定为：`Router → Service/Identity Dependency → Repository → SQLAlchemy Session → PostgreSQL`。任何 Service、Router、Agent 或 Workflow 均不得反向访问 ORM Session 或编写 SQL。

## 3. 数据与事务设计

### 3.1 `users`

| 字段 | 约束/用途 |
| --- | --- |
| `id` | PostgreSQL UUID 主键，服务端生成 |
| `username` | `VARCHAR(64)`、非空、唯一；数据库约束名为 `uq_user_username` |
| `password_hash` | `VARCHAR(255)`、非空；只在 Repository/Service 内部使用，不出现在响应 |
| `created_at` / `updated_at` | PostgreSQL 时间戳和更新时间触发器 |

### 3.2 `candidates`

| 字段 | 约束/用途 |
| --- | --- |
| `id` | PostgreSQL UUID 主键，服务端生成 |
| `user_id` | 非空、唯一、外键指向 `users.id`；建立一对一归属锚点 |
| `name` | 可空，最长 64 字符 |
| `created_at` / `updated_at` | PostgreSQL 时间戳和更新时间触发器 |

注册事务由 `UserRepository.create_with_candidate()` 执行：先检查用户名，再在同一事务中加入 User 和 Candidate 并 flush。用户名竞争由数据库唯一约束兜底；任一写入失败时整体回滚，不允许产生只有 User 或只有 Candidate 的半成品。

### 3.3 身份事实来源

JWT 只携带 `sub=user_id` 及标准安全声明；`candidate_id`、用户名、姓名和 profile 状态均以 PostgreSQL 当前数据为准。每次受保护请求均执行：`Bearer Token → JWT 校验 → user_id → UserRepository.get_by_id → CandidateRepository.get_by_user_id → CurrentIdentity`。

## 4. API 契约设计

### 4.1 注册

`POST /api/v1/auth/register`

- 输入：`username`、`password`、可选 `name`。
- 成功：HTTP `200`，返回短期 `access_token`、`token_type=Bearer`、`expires_in` 和最小 User/Candidate 身份。
- 重复用户名：HTTP `409`，统一冲突错误；不得返回数据库异常细节。
- 输入非法：统一 `400`，不返回密码原值。

### 4.2 登录

`POST /api/v1/auth/login`

- 输入：`username`、`password`。
- 成功：与注册返回同一版本化响应结构。
- 用户不存在、密码错误、Candidate 关联缺失：统一 HTTP `401` 和 `authentication failed`，不区分账户存在性。

### 4.3 当前身份

`GET /api/v1/auth/me`

- 输入：`Authorization: Bearer <access_token>`。
- 成功：HTTP `200`，返回 `user_id`、`candidate_id`、`username`、可选 `name` 和 `profile_status`。
- 缺失、无效、过期 Token 或 User/Candidate 关联异常：统一 HTTP `401`。
- 不接受请求体中的 `user_id` 或 `candidate_id` 作为身份依据。

所有成功和失败路径均通过统一响应包装 `{code, msg, data}`；错误 `data` 为 `null`，不暴露哈希、Token、连接串、SQL 或堆栈。

## 5. 安全设计

- 密码使用随机盐 `scrypt` 哈希；数据库只存哈希串。
- JWT 密钥由服务端 `SecretStr` 配置提供，长度至少 32；签发方、受众、`iat`、`exp` 和 `sub` 必须校验。
- Access Token 为短期令牌；本期不设计 Refresh Token、服务端会话、登出、密码找回或 Token 轮换。
- 日志只记录方法、路径、状态、耗时和请求关联 ID；禁止记录密码、哈希、Token、完整连接串和用户敏感身份数据。
- 认证错误采用统一语义，避免用户名枚举。

## 6. 失败处理与一致性

| 失败点 | 处理 | 数据结果 |
| --- | --- | --- |
| Pydantic 输入失败 | 返回 `400` 统一校验错误 | 不访问数据库 |
| 用户名已存在 | 返回 `409` | 事务不产生新记录 |
| PostgreSQL 连接/迁移不可用 | 阻断注册、登录和身份解析，记录脱敏分类 | 不接受降级到内存或 Mock |
| 密码校验失败 | 返回统一 `401` | 不泄露账户状态 |
| JWT 校验失败 | 返回统一 `401` | 不访问后续业务资源 |
| Candidate 缺失或归属不一致 | 返回统一 `401` | 不构造可信身份 |
| 注册事务任一步骤异常 | 回滚整个事务并返回安全服务错误 | 禁止半初始化 User/Candidate |

本模块没有异步任务、外部副作用或需要重试的发送操作，因此不引入队列、Celery、Redis 限流或补偿状态机。

## 7. 设计一致性检查与变更记录

### 7.1 与阶段 1/2 的一致性

- 范围一致：仅注册、登录、`/auth/me` 和 PostgreSQL 用户初始化。
- 依赖一致：PostgreSQL 16 有真实预验证证据；Redis 认证限流已明确移除。
- 权限一致：身份由 JWT 验签后回到 Repository 复核，不能信任客户端身份字段。
- 数据一致：User/Candidate 一对一关系由数据库唯一约束和单事务保证。

### 7.2 密码契约裁决

开发者确认采用阶段 1 的最小约束：密码非空且最长 128 字符，不要求大小写、数字或特殊字符组合。阶段 4 已将该契约对齐列为独立任务，阶段 5 只删除过度校验，不改变 scrypt、JWT、数据库结构或 API 响应。

### 7.3 本次范围变更记录

2026-07-31，开发者裁决移除认证 Redis 限流。受影响内容：认证 Router 依赖、认证限流配置、429/503 限流错误映射、限流单元测试及认证发布检查。未受影响内容：项目其他模块的 Redis 基础设施、PostgreSQL 数据模型、JWT、Repository 和 API 核心契约。

## 8. 回滚与迁移策略

- 应用回滚：恢复上一个已验证 Backend 版本；不回滚无关模块的 Redis 或任务配置。
- Schema 回滚：仅在数据库尚未承载需保留的账户数据且获得批准时，按 `04-data/rollback.sql` 或 Alembic 反向迁移删除本次新增对象；否则只回滚应用，保留 User/Candidate Schema。
- 注册失败回滚：由数据库事务自动回滚 User/Candidate 创建，不提供手工补偿写入。
- 认证限流移除不需要数据库迁移。

## 9. 方案评审门禁

阶段 3 通过前，开发者需确认：

1. 本方案边界与阶段 1 需求裁决一致；
2. PostgreSQL 是本模块唯一关键路径外部运行时依赖，阶段 2 证据可追溯；
3. User/Candidate 数据约束、API 错误语义、身份复核链和失败处理已明确；
4. 密码输入约束已按“非空且最长 128 字符”完成裁决，并有对应实现任务；
5. 无未处理的范围、数据、权限、依赖或回滚阻塞项。
