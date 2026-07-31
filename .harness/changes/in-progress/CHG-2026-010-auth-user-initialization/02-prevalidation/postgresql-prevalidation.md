# PostgreSQL 真实预验证记录

## 裁决与范围

- 阶段：2，外部技术能力预验证。
- 状态：`passed`。
- 开发者确认：2026-07-31。
- 本模块的唯一关键路径外部运行时依赖：PostgreSQL 16。
- 不在本记录范围：Redis 认证限流。该能力已从认证模块的范围与实现中移除；项目其他模块是否使用 Redis 不影响本裁决。

## 验证目标

证明认证模块可以在真实 PostgreSQL 服务上完成迁移、原子初始化和身份复核，而不是只依赖 Mock、内存替身或配置存在性。

## 已复核的真实证据

| 项目 | 结果 | 可审计证据 |
| --- | --- | --- |
| 服务拓扑 | 通过 | `careerpass-backend/docker-compose.integration.yml` 使用 `postgres:16-alpine`，将宿主机 `54329` 映射到容器 `5432`，并通过 `pg_isready` 健康检查。 |
| 凭据注入路径 | 通过 | Compose 将 `DATABASE_URL` 注入 Backend；变更记录仅使用脱敏连接信息，不保存完整连接串或密钥。 |
| 迁移与 Schema | 通过 | 2026-07-25 真实集成测试中，Alembic 重复升级至 `head` 成功，并检查 `users`、`candidates` 表及更新时间触发器。见 `06-verification/test-report.md`。 |
| 原子初始化 | 通过 | 同一真实数据库会话中，`UserRepository.create_with_candidate()` 创建一对一 User/Candidate；注册服务不直接访问 ORM Session。见 `06-verification/test-report.md`。 |
| 身份复核 | 通过 | 真实服务测试覆盖注册、登录和 `/api/v1/auth/me`，身份解析从 JWT 回到 Repository 复核 User 与 Candidate 关联。见 `06-verification/test-report.md`。 |

## 最小真实调用链

`Backend 进程` → `DATABASE_URL` → `PostgreSQL 16 Compose 服务` → `Alembic upgrade head` → `users/candidates` → 注册原子创建 → 登录与 `/auth/me` Repository 复核。

此前的真实集成测试执行命令为 `uv run pytest -m integration`，报告结果为 `1 passed, 78 deselected`（2026-07-25）。该历史运行同时启动了 Redis，但认证路径的 PostgreSQL 证据可独立复核；Redis 结果不作为本阶段的通过依据。

## 不可用时处理

若 PostgreSQL 无法连接、迁移未到目标版本或 User/Candidate Repository 不可用，注册、登录和受保护身份读取均不进入降级模式，模块应阻断并回到阶段 2 排障；不得以 Mock 成功替代真实服务证据。
