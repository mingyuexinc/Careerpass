# 发布与回滚计划

## 发布前置条件

- 方案、任务拆分、测试计划已评审，变更包由 `proposed` 移至 `ready`。
- 依赖版本在 `pyproject.toml`/锁文件固定，并完成安全审查。
- PostgreSQL、Redis、Celery 的非生产凭据已在目标环境以受控方式配置；真实密钥不写入仓库或发布记录。
- 静态检查、单元测试、集成测试均通过，整体覆盖率 >=80%、核心逻辑 100%。
- Alembic 空基线在新建数据库和重复执行场景均验证通过。

## 质量与集成命令

在 `careerpass-backend/` 目录执行：

```powershell
uv sync --frozen --all-groups
uv run ruff check .
uv run pytest
```

真实依赖集成验证使用隔离的 Docker Compose 栈；测试密码仅用于本地/CI 容器，禁止复用于任何环境：

```powershell
docker compose -f docker-compose.integration.yml up --build -d
$env:RUN_INTEGRATION_TESTS = "true"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://careerpass:careerpass_test_only@localhost:5432/careerpass"
$env:TEST_REDIS_URL = "redis://localhost:6379/0"
uv run pytest -m integration
docker compose -f docker-compose.integration.yml down --volumes --remove-orphans
```

集成测试通过前不得将 `1 skipped` 的默认测试结果作为集成或预发验证通过的证据。

## 发布步骤

1. 部署包含应用、迁移配置和锁定依赖的候选构建。
2. 在目标环境执行 `alembic upgrade head`；确认没有领域 DDL 或数据修改。
3. 启动应用，检查结构化启动日志不含敏感数据。
4. 调用 `/health/live` 和 `/health/ready`，确认 200 与请求 ID。
5. 验证 Redis/Celery 探针配置和受控失败行为；不触发真实业务任务。
6. 在观察窗口内记录可用性、错误率、依赖检查耗时和任务失败率。
7. 验证 Worker 已启动并仅注册允许的任务；不得在 Phase 0 触发任何业务任务或外部投递。

## 观测指标

- 应用启动失败次数、就绪检查成功率、readiness 依赖耗时与超时次数。
- HTTP 5xx 比例、异常类型分布、请求 ID 可关联率。
- Redis/Celery 连接失败与探针任务失败/重试次数。
- 日志脱敏测试结果；生产日志抽样不得含敏感字段。

告警不得携带原始请求体、令牌、连接串或候选人资料。

## 回滚步骤

1. 若启动、迁移或冒烟失败，停止发布并恢复上一稳定应用镜像与对应配置。
2. 本变更仅含空 Alembic 基线，不执行 schema downgrade；保留基线记录不会影响后续迁移。
3. 关闭新增 Celery 探针路由和健康检查流量（如配置了网关路由），确认不存在待处理业务任务。
4. 检查错误日志与部署记录，确保没有因故障处理泄露敏感配置；形成发布/回滚记录。
