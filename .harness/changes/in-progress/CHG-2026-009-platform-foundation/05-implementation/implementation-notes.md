# 实现说明

## L0 已完成内容

- 将 `CHG-2026-009` 从 `proposed` 切换至 `in-progress`，目录状态与 `change.yaml` 状态一致。
- 以 `.harness/wiki/Interface protocol.md` 为权威来源，确认统一响应信封为 `{code, msg, data}`。
- 修复 `.harness/rules/Coding specification.md` 中的响应格式排版，并显式禁止 `message` 字段。
- 增加本变更包内的响应契约，明确成功、错误、分页、请求追踪和后续变更控制规则。

## 未实施内容

L1 至 L5 均未开始：没有创建 FastAPI 应用、配置模型、日志中间件、数据库连接、Alembic、Redis/Celery、健康检查或测试代码。本层不产生运行时行为和数据库变更。

## 正式工程路径

L0 仅修改 Harness 规范与变更包，未修改 `careerpass-backend/` 内的工程源码。

## L1 已完成内容

- 在 `careerpass-backend/app/` 建立最小 FastAPI 应用工厂和 API 路由边界；根路径仅用于验证响应契约，不探测外部依赖。
- 在 `app/core/config.py` 提供基于 Pydantic Settings 的应用配置，支持 `development`、`test`、`production`，并拒绝生产环境开启 `DEBUG`、空服务名和非法环境值。
- 在 `app/schemas/response.py` 和 `app/core/exceptions.py` 实现统一成功/失败信封及验证、HTTP、已知应用、未知异常的映射。
- 未知异常日志只记录请求方法、路径和异常类型，不记录异常消息或堆栈，避免在 L1 引入敏感数据泄露路径。
- 在 `tests/` 中提供配置、响应工厂、应用工厂和异常契约测试；项目依赖固定在 `pyproject.toml` 与 `uv.lock`。

## L1 边界确认

没有创建外部服务客户端、ORM Session、Repository、业务 Service 或业务数据表。请求 ID、结构化日志、数据库、Redis/Celery 和健康检查仍属于后续层。

## L2 已完成内容

- 在 `app/core/request_context.py` 建立基于 `ContextVar` 的请求关联上下文：合法上游 `X-Request-ID` 透传，缺失、非法或超过 64 字符的值替换为服务端 UUID。
- 在 `app/core/middleware.py` 增加 HTTP 中间件。每个正常响应都会返回 `X-Request-ID`，并仅记录方法、无查询参数的路径、状态码和耗时。
- 在 `app/core/logging.py` 实现 JSON 结构化格式、字段级递归脱敏和日志命名空间过滤。Authorization、Cookie、密码、令牌、连接串、邮箱、电话、地址、简历/原文等字段会被替换；结构化处理器只接收 `careerpass.*` 记录，拒绝第三方库记录。
- 未处理异常保留既有的安全响应，并利用请求状态为其响应补充 `X-Request-ID`；日志仅记录异常类型。
- 为请求 ID、递归脱敏、JSON 格式白名单、第三方日志过滤及成功/404/409/500 响应头补充测试。

## L2 边界确认

未记录请求体、查询参数、认证头、Cookie、异常消息或堆栈。L2 不实现日志采集平台、分布式追踪平台、数据库、Redis/Celery 或健康检查；这些能力仍由后续层负责。

## L3 已完成内容

- 在 `app/infrastructure/database/` 建立唯一的 SQLAlchemy 2.0 异步基础设施入口：`Base`、PostgreSQL `AsyncEngine`、`async_sessionmaker` 和幂等释放的 `Database` 生命周期对象。
- `DATABASE_URL` 现为 Pydantic Settings 的必填 `PostgresDsn`；`database_pool_size` 受 1–20 的边界校验。真实 `.env` 已加入 Git 忽略，示例只使用不可用占位凭据。
- 应用 lifespan 在启动时仅创建引擎与会话工厂、写入 `app.state.database`，关闭时释放引擎；不在启动阶段连接数据库，不暴露 Session 给 API/Service。
- 在 `alembic/` 建立异步 Alembic 环境，并增加 `20260723_0001` 空基线 revision。该 revision 不含表、枚举、函数、触发器或领域数据 DDL。
- 新增 `app/repositories/` 作为数据访问边界，并以架构测试禁止 API、Service、Agent、Workflow 层 import SQLAlchemy 或 `AsyncSession`。

## L3 边界确认

本层未创建任何业务 Schema，故按变更包规则不提供 `04-data/db-migrations.sql`、`rollback.sql` 或领域 Alembic revision。首个业务闭环的 Schema 变更必须独立提供这些审阅产物，并通过 Alembic 执行。

## L4 已完成内容

- 在 `app/infrastructure/cache/` 建立 Redis 异步客户端与幂等关闭边界；在 `app/infrastructure/tasks/` 建立 Celery 工厂，固定 JSON 序列化、结果后端、任务状态、超时、延迟确认和瞬态连接/超时异常的指数退避重试。
- 增加 `careerpass.runtime_probe` 无副作用任务：输入通过 Pydantic 校验，使用显式幂等键，成功结果和失败状态均由 Celery 记录；无效输入直接失败而不进行无效重试。
- 在 `app/infrastructure/runtime.py` 建立 PostgreSQL/Redis 的超时有界探测，以及只验证本地安全配置的 Celery 探测；失败原因不向外传播或记录为敏感日志。
- 在 `app/services/runtime_health_service.py` 通过注入的探测器聚合运行态，避免 API 层直接访问引擎、Redis 或 Celery。
- 新增 `/health/live` 与 `/health/ready`。liveness 不访问外部依赖；readiness 在任一依赖失败时以统一 `{code:500,msg:"service not ready",data:null}` 返回 HTTP 503，不泄露网络、连接串或堆栈。
- 应用 lifespan 统一管理数据库、Redis 和 Celery 运行态对象；Redis、Celery 的连接不会在启动阶段被强制建立。

## L4 边界确认

本层未接入真实 Worker、Redis、PostgreSQL 或监控平台，也未创建业务异步任务和任务状态表。真实依赖联通性、Worker 部署、重复任务持久化审计与生产告警将在 L5 集成、发布和观测阶段验证。

## L5 已完成内容

- 在 `pyproject.toml` 固化默认质量门禁：Ruff 的 E/F/I 规则、pytest 覆盖率报告和全局 80% 阈值；当前应用代码实际覆盖率为 100%。
- 增加 Worker 入口 `app.infrastructure.tasks.worker:celery_app`，使容器和生产进程可以加载与应用相同的受控 Celery 配置和任务注册。
- 增加受 `RUN_INTEGRATION_TESTS=true` 控制的集成测试：对隔离 PostgreSQL 重复执行 `alembic upgrade head`，并以真实 PostgreSQL/Redis 验证 readiness；默认本地单测不会尝试连接外部服务。
- 增加 `Dockerfile`、`.dockerignore` 和 `docker-compose.integration.yml`，编排 PostgreSQL 16、Redis 7.4、后端和 Celery Worker。
- 增加 GitHub Actions 工作流：先执行锁定依赖、Ruff 和覆盖率测试，再启动 Compose、探测 `/health/ready` 并执行真实依赖集成测试；无论结果如何都清理 Compose 资源。

## L5 验证边界

本机未发现可用的 `docker` 命令，因此 Compose 集成演练、真实 Worker 连通性、预发发布和回滚尚未在本地执行；相应命令已写入发布计划和 CI。不得将默认跳过的集成测试视为真实依赖联调通过。
