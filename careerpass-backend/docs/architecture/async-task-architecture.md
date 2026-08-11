# 异步任务架构

> 本文档描述当前简历解析任务使用的 PostgreSQL、Dispatcher、Redis 和 Celery 运行结构，不定义其他未来任务类型。

## 1. 组件职责

| 组件 | 职责 |
| --- | --- |
| AsyncTaskRun | 任务状态、幂等键、投递租约、执行租约和终态的权威记录 |
| Dispatcher | 从 PostgreSQL 领取待投递任务，发布固定 Celery 任务并确认投递 |
| Redis | Celery Broker；不作为业务状态或 Result Backend |
| Worker | 领取执行租约，运行固定 resume_parse 任务并提交终态 |
| Repository | 任务领取、租约、状态迁移和幂等持久化 |

Dispatcher 是独立进程，不由 Celery Beat 代替。Celery 只接收受控任务名和 task_run_id。

## 2. 执行链路

1. Producer 在业务事务中创建或复用 queued AsyncTaskRun。
2. Dispatcher 以 dispatch_token 和有限租约领取一批 queued 任务。
3. Dispatcher 将固定任务名发布到 Redis，并使用相同令牌确认或释放投递。
4. Worker 根据 task_run_id 从 Repository 复核资源、状态和归属，取得 execution_token。
5. Worker 执行业务流程；成功或失败只能由有效执行令牌提交。
6. Dispatcher 周期性处理租约过期的卡死任务。

## 3. 可靠性

- idempotency_key 保证同一资源和版本只建立一个有效任务。
- task_acks_late、worker_lost 重投递和 Redis visibility timeout 支持至少一次交付。
- 至少一次交付不等于至少一次业务写入；Repository 状态和执行令牌阻止重复终态。
- 发布失败释放投递租约，进程中断依赖租约过期重新领取。
- 超时、临时连接错误可以在配置上限内重试；业务不可重试错误直接进入 failed。

## 4. 状态边界

合法主路径为 queued → running → succeeded，以及 queued/running → failed。Celery 事件、返回值和 Redis 数据不得覆盖 AsyncTaskRun。

Resume 与 AsyncTaskRun 的解析终态需要在业务事务中保持一致；迟到 Worker 或旧令牌必须安全失效。

## 5. 运行边界

当前 Compose 提供 PostgreSQL、Redis、Backend、Worker 和单独 Dispatcher。真实拓扑是否可用必须由相关 Slice 的 Readiness Check 和 Verify 证据确认，不能由配置文件存在推导。
