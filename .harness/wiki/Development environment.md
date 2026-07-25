# 开发环境与真实集成测试说明

本文档约定职达 Agent 本地开发、Docker Compose 依赖服务及真实集成测试的运行方式。它用于复现认证与用户初始化等功能的数据库、缓存与 API 联调条件；不记录任何生产凭据或个人密钥。

## 1. 服务与版本

| 服务 | Compose 服务名 | 镜像/运行时 | 用途 |
| --- | --- | --- | --- |
| PostgreSQL | `postgres` | `postgres:16-alpine` | 业务数据、Alembic 迁移与 Repository 集成验证 |
| Redis | `redis` | `redis:7.4-alpine` | 缓存与 Celery Broker/Backend 的依赖连通性验证 |
| Backend | `backend` | 本项目 Dockerfile | FastAPI API 联调 |
| Worker | `worker` | 本项目 Dockerfile | Celery 异步任务运行时 |

集成环境编排文件为 `careerpass-backend/docker-compose.integration.yml`。服务间使用 Compose 的默认网络互联，因此容器内部应使用服务名 `postgres`、`redis`，而不是 `localhost`。

## 2. 端口约定与当前状态

| 服务 | 容器端口 | 宿主机约定端口 | 当前 Compose 状态 | 使用场景 |
| --- | --- | --- | --- | --- |
| PostgreSQL | `5432` | `54329` | 已映射 | 从宿主机执行 pytest、数据库客户端调试 |
| Redis | `6379` | `63790` | 已映射 | 从宿主机执行 pytest、缓存客户端调试 |
| Backend | `8080` | `8080` | 已映射 | 访问 `http://localhost:8080` |

`54329` 与 `63790` 是为避免占用常见本机端口而约定的宿主机端口，已在当前 Compose 文件中配置。对应配置如下：

```yaml
postgres:
  ports:
    - "54329:5432"
redis:
  ports:
    - "63790:6379"
```

端口映射仅用于本地开发，不应在生产部署中默认开放。

## 3. 环境变量

### 3.1 应用运行时变量

| 变量 | 用途 | 本地/Compose 示例 | 规则 |
| --- | --- | --- | --- |
| `APP_ENV` | 运行环境 | `test` / `production` | 真实集成测试使用 `test` |
| `DATABASE_URL` | 应用连接 PostgreSQL | `postgresql+asyncpg://careerpass:***@postgres:5432/careerpass` | 容器内使用服务名；不得写入生产密码 |
| `REDIS_URL` | 应用连接 Redis | `redis://redis:6379/0` | 容器内使用服务名 |
| `JWT_SECRET_KEY` | JWT 签发与验签 | 至少 32 字符的本地随机值 | 不提交真实值，不写入日志或响应 |
| `AUTH_RATE_LIMIT_ENABLED` | 认证路由 Redis 限流开关 | `true` | 生产环境必须为 `true` |
| `AUTH_RATE_LIMIT_REQUESTS` | 单窗口允许认证请求数 | `10` | 按客户端 IP 与认证路径计数 |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | 限流窗口长度 | `60` | 必须为正整数 |
| `AUTH_RATE_LIMIT_TIMEOUT_SECONDS` | Redis 限流调用超时 | `0.2` | 超时或 Redis 不可用时安全返回 `503` |
| `READINESS_TIMEOUT_SECONDS` | 就绪检查超时 | `2` | 必须为有限值 |
| `CELERY_TASK_TIME_LIMIT_SECONDS` | Celery 任务时间限制 | `30` | 必须为有限值 |

### 3.2 宿主机真实集成测试变量

在已按第 2 节映射端口后，在 PowerShell 会话中设置：

```powershell
$env:RUN_INTEGRATION_TESTS = "true"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://careerpass:careerpass_test_only@localhost:54329/careerpass"
$env:TEST_REDIS_URL = "redis://localhost:63790/0"
$env:JWT_SECRET_KEY = "replace-with-a-local-random-secret-of-at-least-32-characters"
```

`RUN_INTEGRATION_TESTS` 是显式开关；未设为 `true` 时，`tests/integration/test_runtime_dependencies.py` 必须跳过，以防测试误连非隔离环境。`TEST_DATABASE_URL` 和 `TEST_REDIS_URL` 只用于该真实集成测试文件，不得指向个人、共享或生产服务。

`careerpass_test_only` 仅是隔离的本地 Compose 示例密码，不得复用于任何共享或生产环境。真实本地配置应放在仓库忽略的 `.env` 文件中；如未来加入 `.env.example`，其中只能包含变量名和安全占位值。

## 4. 启动、健康检查与停止

在 `careerpass-backend` 目录执行以下命令：

```powershell
docker compose -f docker-compose.integration.yml pull postgres redis
docker compose -f docker-compose.integration.yml up -d postgres redis
docker compose -f docker-compose.integration.yml ps
docker compose -f docker-compose.integration.yml exec postgres pg_isready -U careerpass -d careerpass
docker compose -f docker-compose.integration.yml exec redis redis-cli ping
```

预期状态：PostgreSQL 显示 `accepting connections`，Redis 返回 `PONG`，并且 Compose 状态为 `healthy`。完成后可停止依赖服务：

```powershell
docker compose -f docker-compose.integration.yml down
```

`down` 会停止并移除容器及网络；未加 `-v` 不会删除命名卷。若需要清空本地测试数据，删除卷前必须确认目标仅为该集成环境。

## 5. 真实集成测试流程

认证与用户初始化的真实集成测试位于 `careerpass-backend/tests/integration/test_runtime_dependencies.py`，覆盖以下链路：

1. Alembic 升级可重复执行，且 `users`、`candidates` 表和更新时间触发器存在。
2. Repository 原子创建 `User + Candidate`，并可按用户重新解析候选人。
3. `/api/v1/auth/register`、重复注册、`/login`、`/me` 与 `/health/ready` 在真实 PostgreSQL/Redis 依赖下返回预期结果。

依赖服务健康、端口映射和第 3.2 节变量均已就绪后执行：

```powershell
uv run pytest -m integration
```

只有该命令实际通过，才能将第 7 阶段“集成测试”标记为通过；仅通过使用替身的单元/API 测试，或仅启动容器，均不能替代真实依赖验证。

## 6. 常见问题与排查

| 现象 | 排查与处理 |
| --- | --- |
| pytest 被跳过 | 确认 `RUN_INTEGRATION_TESTS=true`，并同时设置 `TEST_DATABASE_URL`、`TEST_REDIS_URL`。 |
| 连接 `localhost` 被拒绝 | 确认第 2 节端口映射仍存在并已重建服务；使用 `docker compose ... ps` 确认宿主机端口已发布。 |
| 服务未健康 | 使用 `docker compose -f docker-compose.integration.yml logs postgres redis` 查看日志，确认端口未冲突和 Docker Engine 已运行。 |
| 迁移失败 | 确认连接的是隔离测试库，检查 `alembic.ini` 与 `TEST_DATABASE_URL` 的驱动、用户名和数据库名。 |
| `/health/ready` 失败 | 分别验证 PostgreSQL 的 `pg_isready` 和 Redis 的 `redis-cli ping`，不要在日志中输出连接字符串中的密码或 JWT。 |

## 7. 安全与变更要求

- `.env` 必须保持在 `.gitignore` 中；提交前检查没有密钥、访问令牌或真实连接凭据。
- 容器内部服务地址与宿主机调试地址是两套地址；修改端口或凭据时，须同步更新 Compose、本文档和集成测试运行变量。
- 新增依赖、端口、环境变量或健康检查时，须在本文档补充用途、默认值/占位值、连通性检查及回滚方式。
- 真实联调产生的数据仅限隔离环境；不得将测试数据库、缓存或日志作为业务数据来源。
- 认证路由按客户端 IP 和路径在 Redis 中实施固定窗口限流；超过阈值返回统一响应的 `429`，Redis 限流依赖不可用时返回统一响应的 `503`，不得静默绕过。
