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

    docker compose -f docker-compose.integration.yml up -d --build
    docker compose -f docker-compose.integration.yml ps

宿主机端口为 PostgreSQL 54329、Redis 63790、Backend 8080。容器内部通过 postgres、redis 服务名连接。

Worker 镜像固定安装已验证的 MinerU Bridge，不在任务运行时动态下载。若宿主机访问 MinerU 依赖本地代理，先在未提交的 `.env` 中设置 `CAREERPASS_CONTAINER_PROXY`，地址使用 `host.docker.internal`，不能在容器中沿用宿主机的 `127.0.0.1`。

停止环境：

    docker compose -f docker-compose.integration.yml down

不要在未确认目标卷属于本项目隔离环境前删除卷。

## 4. 验证

开始首个 Slice 或前后端联调前，先完成基础服务基线检查：

    docker compose -f docker-compose.integration.yml config --quiet
    docker compose -f docker-compose.integration.yml up -d --build
    docker compose -f docker-compose.integration.yml ps
    curl http://localhost:8080/health/live
    curl http://localhost:8080/health/ready

确认 PostgreSQL、Redis、迁移、Backend、Worker 和 Dispatcher 正常后，再执行 Slice 的单元、接口、集成和前后端端到端验证。基础服务异常时先查 `docs/development/backend-troubleshooting.md`，不要把环境故障归因于当前 Slice。

    uv run pytest
    uv run pytest -m integration
    uv run ruff check .

integration 测试需要隔离 PostgreSQL/Redis 和相应显式环境变量。external_integration 测试需要受控样本、显式开关和真实凭证；普通测试通过不能替代外部能力验证。

## 5. 安全

- .env、令牌、真实连接密码和敏感样本不得提交。
- 日志和测试报告不得包含简历正文、内部对象路径或模型原始响应。
- 本地 Compose 凭据只用于隔离测试，不得复用于共享或生产环境。

故障排查见 docs/development/backend-troubleshooting.md。
