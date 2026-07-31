# 异步任务技术方案

## 1. 定位与适用范围

本方案是异步任务运行机制的唯一技术权威来源。它适用于简历解析及已由 [Agent 工作流编排技术方案](Agent%20workflow%20orchestration%20technical%20design.md) 决定调度的后台执行；岗位 JD 的受控启动导入不创建异步任务；`candidate_documents` 是原始附件资源，不创建异步任务。

`async_task_runs` 的表结构、约束、枚举和索引以 [数据模型](../03-contracts/Data%20model.md) 为准；资源的业务状态、下游准入和用户可见行为以 [业务规则与状态机](../02-domain/Business%20rules%20and%20state%20machines.md) 为准。

## 2. 依赖与职责

Redis、Celery Worker 和独立 Dispatcher 是简历异步解析的 MVP 正式运行依赖。首次交付必须完成 Redis Broker、Worker 和 Dispatcher 的真实连通性验证。

| 组件 | 职责 |
| --- | --- |
| PostgreSQL / `async_task_runs` | 业务任务运行、可靠入队记录、幂等约束、终态失败审计的权威来源 |
| Redis | Celery Broker；不启用 Celery Result Backend。Redis 也可继续服务于认证限流，但不缓存候选人资料或业务任务权威状态 |
| Dispatcher | 独立单实例扫描待投递记录并投递 Celery；不由 Celery Beat 驱动 |
| Worker | 原子领取任务、执行解析、重试并持久化终态业务结果 |

## 3. 可靠入队与执行流程

1. 简历资源创建时，在同一数据库事务创建 `async_task_runs(status=queued, celery_task_id=NULL)`；任务幂等键为 `{task_type}:{resource_id}:{task_version}`。
2. Dispatcher 通过 Repository 和数据库行锁领取 `queued + celery_task_id IS NULL` 的有限批次记录，向 Broker 投递。
3. Broker 接受后回填确定性的 `celery_task_id`。投递与回填之间中断时，可重新投递同一任务运行 ID；Worker 必须以原子领取和幂等写入避免重复业务结果。
4. Worker 仅在资源仍有效、对象可读取且归属链有效时执行。成功时先完成结构化与业务校验，再原子写入结果和资源终态；失败时只写入允许暴露的脱敏 `failure_code`。

资源状态与任务状态必须分离：资源在队列、运行或重试期间维持 `processing`；任务运行使用 `queued / running / succeeded / failed`。任务运行状态不是用户资源的可用性判断依据。

## 4. 幂等、并发与版本

- 同一资源、任务类型和版本只允许一个有效任务运行；重复 API 请求、Celery 至少一次投递、重复回调均复用任务运行。
- Worker 的领取、状态写入和成功回调必须使用原子条件更新或等价并发控制。
- `task_version` 在 MVP 固定为内部常量 `v1`，仅用于既有幂等键；不讨论版本升级、历史重跑或多版本并存。
- 对已 `succeeded`、`failed` 或归属链失效资源的重复回调必须安全忽略并记录脱敏审计。

## 5. 重试、超时与失败分类

可重试故障仅限网络超时、依赖暂不可用、限流和其他临时故障。格式不支持、文件损坏、结构化校验失败等确定性故障不得无限重试。

`parse_failure_code_enum` 是资源终态失败原因的唯一权威来源；不得在资源表保存自由文本 `parse_error`。MVP 统一采用以下基线策略，不为不同解析器建立差异化策略：

| 项目 | MVP 基线 |
| --- | --- |
| 单次软超时 | 25 秒 |
| 单次硬超时 | 30 秒 |
| 可重试故障 | 网络超时、依赖暂不可用、限流及 `parser_timeout` 等临时故障 |
| 不重试故障 | 格式不支持、文件损坏、Schema/业务校验失败及其他确定性输入错误 |
| 最大重试次数 | 2 次 |
| 重试间隔 | Celery 指数退避，启用抖动，单次等待最多 60 秒 |
| 结果权威来源 | PostgreSQL 的 `async_task_runs` 与业务资源状态；不使用 Celery Result Backend |

跨重试总截止时间、任务级差异化重试、复杂队列路由和长期任务监控优化均为后续能力；不得阻塞 MVP 实现。重试次数已有限，单次软/硬超时也已确定，任务不得无限执行或无限重试。

## 6. Worker 异常确认、重投递与执行租约

MVP 采用“至少一次投递”，而非“恰好一次投递”。Celery 必须启用 `task_acks_late=true`、`task_reject_on_worker_lost=true` 和 `worker_prefetch_multiplier=1`：任务仅在 Worker 成功完成数据库终态写入后确认；Worker 子进程异常退出时要求 Broker 重投递；单 Worker 不预取多个尚未确认的任务。Redis Broker 的 `visibility_timeout` 统一设为 300 秒，覆盖 30 秒硬超时和最长 60 秒重试退避，并限制主进程/网络异常后的最长自动重投递等待。

Broker 重投递、Dispatcher 在“投递—回填”间中断造成的重复消息，都必须视为正常故障路径，不能以 `celery_task_id` 是否重复作为去重依据。Worker 每次实际执行前必须经 Repository 原子取得数据库执行租约：仅 `queued` 任务，或租约已过期的 `running` 任务可以被领取；领取时写入新的不可预测 `execution_token`、`started_at` 和 90 秒 `execution_lease_expires_at`。执行成功、可重试回排或终态失败时，更新条件必须同时匹配该令牌；令牌不匹配的旧 Worker 只记录脱敏审计并退出，不得写入业务结果或改变资源状态。

可重试异常在调用 Celery `retry` 前，将本次租约释放并使任务回到 `queued`；下一次消息再以新令牌领取。这样，晚到消息、Worker 进程被杀和 Redis 可见性超时均不会产生重复业务结果。资源结果与任务终态写入仍须处于同一数据库事务中。

## 7. 卡死 `running` 任务的兜底

Dispatcher 在其既有轮询循环中（无需引入 Celery Beat）每 60 秒额外扫描一次卡死任务。若任务仍为 `running`、`started_at` 已超过 10 分钟且当前执行租约已过期，则通过带令牌/状态条件的原子更新将任务及对应资源置为 `failed`，资源失败原因统一为 `internal_error`；审计记录使用脱敏的 `task_stalled` 事件名，不保存堆栈或文件内容。

10 分钟窗口显著大于单次 30 秒硬超时和 Redis 300 秒可见性超时，正常的 Broker 重投递有机会先取得新租约；任何新领取、重试或成功完成都会更新 `started_at` 或进入终态，因此不会被该扫描误判。兜底转为终态后，迟到的 Celery 消息必须因状态或令牌不匹配而安全忽略。该机制只处理异常遗留记录，不提供用户可见的人工重跑或通用任务运维后台。

## 8. 安全、审计与可观测性

- Worker 只能按资源 ID 获取经 Repository 授权的输入，禁止接收模型拼接的路径、SQL、Shell 或外部请求。
- 任务记录、Celery 日志、Prompt、LangSmith 追踪和 API 响应不得包含文件正文、文件路径、联系方式、模型原始响应、凭证或堆栈。
- 计划、投递、领取、重试、成功、失败和卡死兜底均记录关联 ID、任务类型、版本、状态和脱敏失败原因。
- 首次交付必须验证 Redis、Worker、Dispatcher 的真实连通性，并覆盖 Dispatcher 在“投递—回填”间中断、重复投递、重试耗尽、超时、Worker 强制退出后的重投递、旧租约迟到写入以及重复回调等故障路径。

## 9. 非目标与待决项

- 不建设通用任务运营后台、用户可见重试接口或人工重跑接口。
- Dispatcher 不使用 Celery Beat。对象清理每小时调度的具体触发器应与 Dispatcher 分离，并在对象存储实现变更中确定。
- Redis 高可用、任务分队列、Worker 并发度和复杂任务运营均为后续运行优化；Celery Result Backend 已明确不启用。
