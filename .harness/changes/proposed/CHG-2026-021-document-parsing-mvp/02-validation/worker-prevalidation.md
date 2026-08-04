# Celery Worker 单独真实运行验证记录

> 本记录包含早期 Docker 不可用时的阻塞证据和后续真实复验。以文档末尾的“真实中断与接管复验”作为当前 Worker 预验证结论；早期 `blocked` 仅保留为历史诊断记录，已被后续真实证据覆盖。

## 验证范围

本记录只验证 Celery Worker 的真实运行能力：Worker 启动、Redis 消费、`resume_parse` 任务注册、数据库租约领取、任务确认和安全边界。MinerU、Qwen、Redis Broker、Dispatcher、对象存储的供应商级证据沿用 `prevalidation.md`，不在本记录重复宣称通过；本记录也不宣称完整 MinerU → Qwen → 画像链路已验收。

## 拟运行拓扑

目标拓扑为 `careerpass-backend/docker-compose.integration.yml`：隔离 PostgreSQL 16、Redis 7.4、Backend、独立 Celery Worker 和 Dispatcher；Worker 使用 Compose 服务名 `postgres`、`redis`，任务入口为 `app.infrastructure.tasks.worker:celery_app`，固定任务名为 `careerpass.resume_parse`。

## 执行记录

| 检查项 | 执行方式 | 结果 |
| --- | --- | --- |
| Docker/Compose 可用性 | 执行 `docker --version` 与 `docker compose version` | `blocked（历史）`：早期环境无法识别 `docker` 命令；后续已通过绝对路径 Docker CLI 启动隔离 Compose |
| Compose 配置检查 | 静态读取 `docker-compose.integration.yml` | `passed`：Worker、Redis、PostgreSQL、Dispatcher 的服务、环境变量、依赖关系和共享对象卷已声明 |
| Worker 入口与任务输入 | 静态检查 `app/infrastructure/tasks/worker.py` | `passed`（静态）：注册 `careerpass.resume_parse`，任务只接受 `task_run_id`，不接受路径、URL、Shell、SQL 或模型参数 |
| Worker 单元行为 | `uv run pytest -q --no-cov tests/unit/test_resume_parse_worker_service.py` | `passed`：6 项单元测试通过；仅证明注入式 Worker 业务逻辑，不构成真实 Redis/Worker 验证 |
| Worker 真实启动与 Redis 消费 | Compose 中启动 Worker 并投递真实 `resume_parse` | `blocked（历史，已覆盖）`：后续真实 Compose 复验通过 |
| PostgreSQL 执行租约 | 真实任务消费后检查 `async_task_runs` 的 `running`、`execution_token` 和终态 | `blocked（历史，已覆盖）`：后续真实租约和终态复验通过 |
| 重复/迟到消息和 Worker 中断 | 两个 Worker/强制终止后验证重投递和令牌围栏 | `blocked（历史，已覆盖）`：后续真实重投递和 Worker 接管复验通过 |

## 未采用的证据

- 未将单元测试、Worker 代码静态检查、Celery eager 模式或 Mock Broker 作为真实 Worker 通过证据。
- 未启动真实业务任务，未访问外部 MinerU/Qwen，未使用真实业务简历或生产/共享 PostgreSQL、Redis、对象目录。
- 第一次带默认覆盖率门槛运行单文件测试时，6 项测试本身通过，但全仓覆盖率为 54.24% 导致命令因全局 `fail-under=80` 退出非零；随后使用 `--no-cov` 重跑确认 6 项单元测试通过。该结果仍不改变真实 Worker 验证为 `blocked` 的结论。

## 安全与清理

本次未启动外部服务、未注入或输出凭证、未创建业务任务、未写入业务数据库或对象存储，因此不存在需要清理的隔离任务和临时对象。现有静态检查和单元测试输出未记录简历正文、路径、对象键、模型响应或凭证。

## 结论与解除条件

历史 Worker 预验证结论：`blocked`（Docker CLI 不可用阶段）。该结论已由后续真实 Compose 复验覆盖。

历史阻塞原因：当时环境没有 Docker CLI，无法在项目拟运行的隔离 Compose 拓扑中证明 Worker 真实连接 Redis、消费 `resume_parse`、取得 PostgreSQL 执行租约、确认任务以及处理重投递/Worker 中断。

解除条件（已满足）：在具备 Docker Engine/Compose 的隔离环境中完成真实 Worker 启动、Redis 消费、数据库租约、成功终态、确定性失败、有限重试、重复/迟到消息和 Worker 中断验证，并补录脱敏结果。

## 2026-08-01 实际运行补录

Docker Desktop 已启动。初始失败原因为 Docker Desktop 未运行，且用户安装目录 `C:\Users\58280\AppData\Local\Programs\DockerDesktop\resources\bin` 未进入当前会话 PATH；使用绝对 Docker CLI 启动隔离 Compose 后，PostgreSQL、Redis、Dispatcher 和 Worker 均正常运行。

真实 Worker 日志确认 Celery 5.6.3 已连接 Compose Redis，注册 `careerpass.resume_parse`，Result Backend 为 disabled。受控任务真实进入 `running` 并取得数据库租约；对象不可用路径按有限重试后写入 `storage_unavailable`，简历终态为 failed，画像数为 0，令牌清理。对该已失败任务重复投递后状态和画像数不变。

真实外部调用任务触发 Celery soft time limit 25s，但当前实现使数据库任务仍停留 `running`，因此超时后的业务终态收敛尚未通过；Worker 中断重投递、迟到令牌和完整成功画像写入也未形成完整证据。本轮测试任务、简历和临时对象元数据已清理，并恢复标准 Compose Worker。

因此阶段 2 当时仍保持 `blocked`；该中间结论已由后续超时修复、成功画像和真实 Worker 中断接管复验覆盖。

## 2026-08-01 修复与复验补录

新增 `AsyncTaskRepository.fail_execution_after_timeout`：Celery `SoftTimeLimitExceeded` 发生时，仅在任务仍为 `running` 且执行租约未过期的条件下，以数据库锁写入 `internal_error`，同时清理执行令牌并将简历置为失败。这样 Celery 中断不会留下永久 `running/processing` 状态。

真实 Compose 复验结果：受控任务在真实 Worker 中完成 MinerU/Qwen 调用，任务为 `succeeded`、租约令牌已清理、画像数量为 1；再次投递同一 `task_run_id` 后仍为 `succeeded` 且画像数量仍为 1。单元测试 6 项全部通过。

Worker 中断恢复的数据库租约和迟到消息边界已有令牌条件保护及重复/迟到交付单元证据，但本轮未完成“执行中强制终止容器后等待 Broker 重投递”的完整真实时序，因此该项仍需后续专门补验。

## 2026-08-01 真实中断与接管复验

本轮使用正式 Dispatcher 创建唯一隔离任务 `1b255d4d-6ca3-4137-92bf-2ccb927b0530`，关联测试简历 `a6551ca7-b2e6-4c10-88f9-0492ac5c7317`。任务经 Dispatcher 投递后观察到 `running` 且执行令牌存在，随后在首次 Worker 执行期间执行 `docker kill`。

新 Worker 启动后等待 Redis visibility timeout，日志于 11:57:05 再次收到同一 Celery task，随后于 11:57:18 完成处理。数据库最终状态为 `succeeded`，执行令牌和租约均清理，画像数量为 1。再次以同一 `task_run_id` 投递后，状态仍为 `succeeded`，画像数量仍为 1。

该结果证明了真实 Worker 丢失后的 Redis/Celery 重投递、新 Worker 接管和最终幂等终态。旧令牌的数据库条件围栏由 `DocumentParsingRepository`/`ResumeParseFinalizationService` 和已有真实 PostgreSQL 租约测试覆盖；本轮未将完整令牌值写入验证记录。隔离任务和简历已清理，标准 Worker 已恢复。

## 当前 Worker 预验证结论

当前结论：`passed`（真实复验）。

已形成的脱敏证据覆盖：真实 Compose Worker 启动、Redis 消费、`careerpass.resume_parse` 注册、PostgreSQL 执行租约、MinerU/Qwen 成功画像、确定性失败、超时终态收敛、重复投递幂等、Worker 强制终止后的 Redis 重投递和新 Worker 租约接管。该结论不替代 CHG-021 阶段 5/6/8 的实现、测试和 G2→G3 跨包联调门禁。
