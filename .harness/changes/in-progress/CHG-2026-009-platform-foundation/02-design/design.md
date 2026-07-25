# 方案设计

## 目标与非目标

### 目标

1. 建立符合工程结构规范的 FastAPI 后端骨架，并让本地开发、测试和部署使用同一装配路径。
2. 把配置、日志、异常、响应格式、数据库会话和异步客户端收敛到可替换的基础设施边界。
3. 建立未来领域迁移的唯一入口（Alembic），并禁止应用代码直接执行 DDL。
4. 让后续业务闭环可以在不重构基础层的前提下实现候选人级权限、异步状态和审计。

### 非目标

- 不实现认证、用户/候选人表、简历上传、文件存储、领域 Repository 或业务 Service。
- 不接入 Qwen、LangChain、LangSmith、Pinecone、Embedding 或 Prompt。
- 不实现通用缓存、业务队列、定时任务、监控平台或部署平台。
- 不以健康检查替代鉴权或权限校验。

## 方案与数据流

```text
HTTP Request
  → Request-ID middleware（读取/生成 ID，写入响应与日志上下文）
  → API router（仅健康检查）
  → response factory / exception handler
  → { code, msg, data }

FastAPI lifespan
  → Settings 校验
  → PostgreSQL engine/session factory
  → Redis client
  → Celery app configuration
  → graceful close

Future domain request
  API → Service → Repository → Infrastructure Session
```

建议目录（仅创建本阶段实际需要的包，不创建空的 Agent/RAG 目录）：

```text
careerpass-backend/
├── app/
│   ├── main.py
│   ├── api/v1/health.py
│   ├── core/{config,errors,exceptions,logging,request_context}.py
│   ├── schemas/{response,health}.py
│   ├── infrastructure/
│   │   ├── database/{base,session}.py
│   │   ├── cache/redis.py
│   │   └── tasks/celery_app.py
│   └── repositories/                 # 仅保留包边界，不实现领域 Repository
├── alembic/
├── tests/{unit,integration}/
├── alembic.ini
└── .env.example
```

## 接口、状态机与权限

### 配置契约

- 配置模型按环境分组：应用、PostgreSQL、Redis、Celery、日志；必填机密项不允许默认值。
- `.env.example` 只包含变量名和非敏感示例；真实 `.env` 被 Git 忽略。
- `APP_ENV` 至少区分 `development`、`test`、`production`；生产环境禁止 `DEBUG=true`。

### 响应和错误契约

| 场景 | HTTP 状态 | `code` | `msg` | `data` |
| --- | --- | --- | --- | --- |
| 成功 | 200 | 200 | `success` | 业务数据 |
| 参数校验失败 | 400/422 | 400 | 安全的校验说明 | `null` |
| 未认证/无权限（为后续预留） | 401/403 | 401/403 | 固定文案 | `null` |
| 未处理异常 | 500 | 500 | `internal server error` | `null` |
| 依赖不可用 | 503 | 500 | `service not ready` | `null` |

`msg` 使用 Harness 协议字段名；`message` 不作为实现契约。

### 健康检查

- `GET /health/live`：进程可接收请求即成功；不调用数据库、Redis 或 Celery。
- `GET /health/ready`：以各依赖的短超时连通性检查得到聚合结果。任何关键依赖失败均返回 503；响应不展示主机、端口、堆栈或原始异常。
- 当前阶段不启用认证；健康端点不得访问任何候选人资源，因此不构成归属校验例外。

### 异步任务状态

探针任务只验证任务路由、序列化、超时和错误映射。任务输入采用 Pydantic 模型或原始标量的白名单，使用显式幂等键；任务状态统一映射为 `queued/running/succeeded/failed`，失败原因经脱敏后记录。实际持久化任务记录的表由首个异步业务闭环单独设计。

## 失败处理与回滚边界

- 启动阶段：必填配置无效时拒绝启动；可选异步依赖配置关闭时不创建客户端。
- 请求阶段：业务异常映射为已知错误；未知异常只写脱敏日志并返回统一 500。
- 连接阶段：Readiness 使用有限超时，不能因外部依赖阻塞请求线程。
- 回滚：不引入业务 DDL、缓存键或外部副作用。部署失败时回滚镜像和配置；空 Alembic 基线可保留，不需执行降级。
