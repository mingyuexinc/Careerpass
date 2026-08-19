# Careerpass 后端

## 1. 环境

- Python 3.12
- PostgreSQL 16
- Redis 7.4
- FastAPI、SQLAlchemy、Alembic、Celery

使用 uv 按 uv.lock 安装依赖：

    uv sync --frozen

从 .env.example 创建未提交的 .env，并至少配置 DATABASE_URL、REDIS_URL 和长度不小于 32 的 JWT_SECRET_KEY。真实 MinerU/Qwen 凭证只在需要运行解析外部测试时配置。

## 2. 本地运行

在 careerpass-backend 目录执行：

    uv run alembic upgrade head
    uv run uvicorn app.main:app --reload

服务启动时会幂等初始化数据库中的受控演示账号 `candidate_01` 和 `hr_01`，不通过注册接口创建；密码不打印、不写入响应或日志。账号初始化失败会阻止服务启动。

## 3. 隔离集成环境

docker-compose.integration.yml 提供 PostgreSQL、Redis、迁移、Backend、Worker 和 Dispatcher：

联调环境可通过 `DEBUG_RESET_ENABLED=true` 开启 S-DBG 当前账号数据恢复；生产环境必须保持关闭。

宿主机端口为 PostgreSQL 54329、Redis 63790、Backend 8080。容器内部通过 postgres、redis 服务名连接。

Worker 镜像固定安装已验证的 MinerU Bridge，不在任务运行时动态下载。若宿主机访问 MinerU 依赖本地代理，先在未提交的 `.env` 中设置 `CAREERPASS_CONTAINER_PROXY`，地址使用 `host.docker.internal`，不能在容器中沿用宿主机的 `127.0.0.1`。

启动、检查、重建、重置和停止操作见第 4 节；不要在未确认目标卷属于本项目隔离环境前删除卷。

## 4. 操作说明

### 4.1 启动和检查隔离环境

开始 Slice 或前后端联调前，在 `careerpass-backend` 目录完成基础服务启动：

    docker compose -f docker-compose.integration.yml config --quiet
    docker compose -f docker-compose.integration.yml up -d --build
    docker compose -f docker-compose.integration.yml ps
    curl http://localhost:8080/health/live
    curl http://localhost:8080/health/ready

确认 PostgreSQL、Redis、迁移、Backend、Worker 和 Dispatcher 正常后，再进行前后端操作。`/health/live` 和 `/health/ready` 应分别返回 HTTP 200；基础服务异常时先查 `docs/development/backend-troubleshooting.md`。

### 4.2 代码变更后重建后端

如果后端源代码已修改，而 Compose 环境已经在运行，必须重新构建并启动 Backend，使容器加载最新代码：

    docker compose -f docker-compose.integration.yml up -d --build backend
    docker compose -f docker-compose.integration.yml ps
    curl http://localhost:8080/health/live
    curl http://localhost:8080/health/ready

只重建 Backend 不等于重置 PostgreSQL 数据库；除非明确需要重新创建隔离环境，不要使用 `down --volumes` 或直接删除数据库卷。前端开发服务器通常不需要因后端代码变更而重建，但应刷新页面后重新登录。

### 4.3 S-DBG 当前账号重置

S-DBG 用于清理当前登录的候选人或 HR 账号在隔离联调环境中产生的业务数据。它按当前 Bearer 身份确定清理范围，不接受客户端提交账号或资源 ID；生产环境必须关闭 `DEBUG_RESET_ENABLED`。

操作步骤：

1. 确认 Compose Backend 使用 `DEBUG_RESET_ENABLED=true`，并按 4.1 或 4.2 启动、重建后端。
2. 确认 `/health/ready` 返回 HTTP 200。
3. 在前端使用需要清理的当前身份登录，进入“使用指南”页的调试恢复入口。
4. 点击重置按钮，等待接口完成；成功后前端会清空本地工作区、清除登录态并返回登录页。
5. 重新登录并确认当前角色的数据已清理；其他账号、账号身份和候选人侧的受保护资料不应被清理。

HR 重置会清理当前 HR 拥有的岗位、岗位解析快照、相关任务，以及这些岗位产生的 `Match`、`Application` 和 `ProgressEvent`。因此，已经推进到 `terminated` 的历史投递也应能够被清理。候选人重置不会由 HR 操作触发。

常见情况：

- 如果后端代码刚修改但前端仍提示历史联调数据未清理，先执行 4.2，不要先重置数据库。
- 如果接口返回 409 且提示任务仍在运行，等待相关任务结束后重试。
- 如果接口返回 409 且确实存在无法安全删除的外部关联，保留数据库现场并查看脱敏日志，禁止直接删除共享数据库或卷。
- 成功响应应为统一 `{code, msg, data}` 包络，`data.reset` 为 `true`；失败时前端保留当前页面和登录态。

### 4.4 停止隔离环境

仅停止容器但保留数据库卷：

    docker compose -f docker-compose.integration.yml down

不要在未确认目标卷属于本项目隔离环境前使用 `down --volumes`，也不要通过手工 SQL 清空全库替代 S-DBG 当前账号重置。

## 5. 测试和质量检查

环境操作完成后，可执行：

    uv run pytest
    uv run pytest -m integration
    uv run ruff check .

integration 测试需要隔离 PostgreSQL/Redis 和相应显式环境变量。external_integration 测试需要受控样本、显式开关和真实凭证；普通测试通过不能替代外部能力验证。

## 6. 安全

- .env、令牌、真实连接密码和敏感样本不得提交。
- 日志和测试报告不得包含简历正文、内部对象路径或模型原始响应。
- 本地 Compose 凭据只用于隔离测试，不得复用于共享或生产环境。

故障排查见 docs/development/backend-troubleshooting.md。
