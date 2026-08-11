# Phase 0 平台基础设施基线

## 变更概述

为 CareerPass 后端建立可运行、可测试、可迁移、可观测的最小工程基线。该变更只提供后续业务闭环共同依赖的能力：应用装配、配置、统一响应与异常、请求追踪与脱敏日志、PostgreSQL/Alembic 接入、Redis/Celery 连通性边界、健康检查和测试脚手架。

不创建用户、候选人、简历等业务表，不提供业务 API，不调用 LLM、向量库或外部招聘平台。业务数据模型由后续按业务闭环的变更通过 Alembic revision 落地。

## 影响模块

- `careerpass-backend/app/main.py`：FastAPI 应用工厂、路由挂载和生命周期。
- `app/core/`：配置、错误码、异常、请求上下文、日志与脱敏。
- `app/api/`、`app/schemas/`：统一响应契约和基础健康检查端点。
- `app/infrastructure/database/`：引擎、会话、Base、Alembic 集成。
- `app/infrastructure/cache/`：Redis 客户端边界。
- `app/infrastructure/tasks/`：Celery 应用和无副作用探针任务。
- `tests/`：测试配置、fixture、单元和集成测试基础。

## 数据库变更

本变更不创建业务 Schema、表、枚举、触发器或领域数据。仅建立 Alembic 迁移运行时与空基线 revision；该 revision 不应包含 DDL。因没有数据库对象变更，不创建 `04-data/db-migrations.sql` 和 `rollback.sql`。

## API 变更

- `GET /health/live`：仅验证进程存活，不访问外部依赖。
- `GET /health/ready`：验证 PostgreSQL、Redis 和 Celery 配置可用；不返回连接串、令牌或内部异常细节。
- 所有响应采用 `{code, msg, data}`；错误响应也保持该外层结构，并回显或生成 `X-Request-ID`。

## Redis 变更

新增 Redis 配置与客户端生命周期管理；不写入业务缓存键。Celery 使用 Redis 作为 broker/result backend 的配置边界，是否启用由环境配置决定。

## 关键约束

- 依赖方向必须符合 API → Service → Repository → Infrastructure；Phase 0 不得为便利而在 API/Service 层直接访问 ORM Session。
- 配置只从环境变量和本地未跟踪的 `.env` 加载；密钥、连接串、令牌不得提交、打印或返回。
- 日志与异常不得输出密码、Authorization、Cookie、数据库连接串、简历内容、联系方式或完整请求体。
- 就绪检查必须有超时；依赖不可用时返回统一错误结构且不泄露原因细节。
- Celery 探针任务必须具有确定的任务 ID/幂等键、状态记录和失败原因；禁止产生业务副作用。

## 关联与实施状态

- 关联需求/变更包：Phase 0；后续简历上传与解析闭环的前置依赖。
- 当前状态：`in-progress`；L0 治理与契约已完成，后续能力层尚未开始。

## 验收标准

- 在无 `.env`、缺少必填配置、依赖不可达时，应用以明确且无敏感信息的方式启动失败或就绪失败。
- 在开发环境配置齐全时，应用启动后 liveness 和 readiness 行为符合设计，且每个响应都符合统一协议。
- Alembic 能校验并执行空基线，且未来迁移可通过单一命令运行。
- 单元测试覆盖配置、异常映射、响应包装、请求 ID 和脱敏；核心逻辑覆盖率为 100%，整体不低于 80%。
- 不存在 Service/Agent/Workflow 直连 Session 或 SQL 的实现；不存在真实 LLM、Pinecone 或业务表实现。
- 实施按 L0-L5 能力层串行门禁推进，不以 11 个原子任务全部并行作为排期或验收单位。

## 回滚方案

发布前或开发阶段回退本变更对应提交。若已部署，只回退应用镜像与环境变量；本变更的 Alembic revision 不含 DDL，因此无需数据库回滚。Redis 和 Celery 未写入业务数据，无数据清理步骤。
