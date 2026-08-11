# 认证与会话管理 API 契约

## 变更概述

在接口协议的模块 API 中新增认证与会话管理模块，定义注册、登录、刷新访问令牌、退出登录和获取当前登录用户接口。

## 影响模块

- 认证与会话管理
- 所有需要当前用户或候选人归属校验的业务模块

## 数据库变更

新增 `candidates.user_id` 的唯一约束 `uq_candidate_user_id`，从数据库层保证一个用户仅关联一个候选人。

`auth_sessions` 表及其 Refresh Token 轮换设计保留在数据模型中，标记为 `Deferred`，不纳入 MVP 数据库迁移。

## API 变更

- 新增 `/api/v1/auth/register`
- 新增 `/api/v1/auth/login`
- `/api/v1/auth/refresh` 与 `/api/v1/auth/logout` 仅保留为 Deferred 设计，不进入 MVP 路由实现
- 新增 `/api/v1/auth/me`
- 明确认证公开接口的 `Authorization` 请求头例外规则

## Redis 变更

无。

## 关键约束

- 注册必须在同一事务中创建用户和唯一关联的候选人。
- Refresh Token 刷新轮换、会话撤销与重放检测属于 `Deferred` 设计，不进入 MVP 实现。
- Token、密码及其哈希不得出现在日志、响应的非必要字段、Prompt 或追踪平台中。

## 回滚方案

先执行本变更的 `rollback.sql` 移除 `uq_candidate_user_id`，再回滚接口和数据模型文档变更。本次不涉及运行时配置。
