# 认证与用户初始化

## 变更概述

实现 MVP Lite 的认证与用户初始化：JWT Access Token 配置、scrypt 密码哈希、注册、登录和当前身份 API；用户与候选人模型、迁移与 Repository；注册时原子创建用户和候选人，以及受保护路由的身份复核。

## 影响模块

- `careerpass-backend/app/core`：认证安全配置与密码/JWT 工具。
- `careerpass-backend/app/schemas`：认证 API 契约。
- `careerpass-backend/app/infrastructure/database`：用户与候选人 ORM 模型。
- `careerpass-backend/app/repositories`：用户及候选人 Repository。
- `careerpass-backend/app/services`：注册、登录应用服务与安全领域错误。
- `careerpass-backend/app/api`：Bearer 身份解析、Redis 认证限流与认证路由。
- `careerpass-backend/alembic`：用户、候选人及审计触发器迁移。
- `careerpass-backend/tests`：配置、安全工具、契约、迁移及集成测试。

## 数据库变更

新增 `users` 与 `candidates`，包括唯一约束、外键以及 `updated_at` 触发器。`UserRepository.create_with_candidate()` 在一个事务中创建一对一账户对；注册 Service 不直接访问 ORM Session 或编写 SQL。

## API 变更

提供 `POST /api/v1/auth/register`、`POST /api/v1/auth/login` 与 `GET /api/v1/auth/me`；成功和失败响应均使用 `{code, msg, data}`。注册冲突返回 `409`，认证失败返回不泄漏原因的 `401`。MVP 仅定义短期 Access Token，不包含 Refresh Token。

## 关键约束

- JWT 密钥、签发方、受众和有效期由服务端配置；密钥最少 32 个字符。
- 密码、密码哈希和 Token 不得写入日志、追踪或非必要响应。
- 身份解析须校验 Token 后经 Repository 复核 User 与 Candidate 的关联。
- 认证路由使用 Redis 固定窗口限流；生产环境禁止关闭限流，Redis 不可用或超时时安全失败。
- `auth_sessions`、Refresh Token 及其迁移仍为 Deferred，不得成为 MVP 阻塞项。

## 当前状态

实现、代码评审、真实 PostgreSQL/Redis 集成测试及本地 Compose 预发等价验证已完成；尚未完成发布审批与实际上线，因此本变更包保持 `in-progress`。发布后方可迁移至 `released`。
