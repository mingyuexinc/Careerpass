# T07 代码评审记录

## 结论

- 评审日期：2026-07-25
- 评审范围：认证配置与契约、用户/候选人模型和迁移、Repository、注册/登录服务、当前身份解析、API 路由、测试与 Compose 配置。
- 结论：通过；无未解决的红色问题。
- 发布状态：仍需人工发布审批；本记录不等同于生产上线授权。

## 评审检查

| 检查项 | 结论 | 证据 |
| --- | --- | --- |
| 分层与数据访问 | 通过 | Service 不导入 SQLAlchemy 或 Session；数据库读写集中于 `UserRepository`、`CandidateRepository`。 |
| 原子初始化与约束 | 通过 | `create_with_candidate()` 使用单事务；`users.username` 与 `candidates.user_id` 均有唯一约束，迁移及重复升级已验证。 |
| 身份与归属 | 通过 | `get_current_identity` 校验 JWT 后经 Repository 重新取得 User 与 Candidate，关联异常统一返回 `401`。 |
| 密码与 Token 安全 | 通过 | scrypt 加盐哈希、JWT 最小声明、响应和日志不包含密码哈希；Token 仅出现在注册/登录的必要响应中。 |
| 认证范围裁决 | 已更新 | Redis 认证限流已于 2026-07-31 从受控 Demo 认证模块移除；认证路由不再依赖 Redis。 |
| API 契约 | 通过 | 正常及错误路径均使用 `{code, msg, data}`。 |
| MVP 范围 | 通过 | Refresh Token/会话持久化明确为 Deferred，已在业务规则中加 MVP Lite 适用性裁决。 |
| 敏感信息 | 通过 | 请求日志仅记录方法、路径、状态和耗时；预发验证记录不保留 Token、完整连接串或凭据。 |

## 质量证据

- `uv run ruff check app tests alembic`：通过。
- `uv run pytest`：`83 passed, 1 skipped`，总覆盖率 `99.09%`。
- `uv run pytest -m integration` 的历史运行曾同时使用 PostgreSQL/Redis；当前认证模块仅将其中 PostgreSQL 证据归档至 `02-prevalidation/postgresql-prevalidation.md`，Redis 限流结论已失效。

## 非阻断项

- Starlette 对 `httpx`/`TestClient` 输出弃用警告；不影响本次测试结论，后续依赖升级任务应处理。
- 全局 `validate_changes.py` 因其他 `proposed/` 目录中的既有非 `CHG-...` 命名包失败；本认证变更包的必填文件、状态与元数据已逐项核对通过。该仓库级治理问题不影响本变更的代码与测试结论，但应在独立维护任务中修复。
