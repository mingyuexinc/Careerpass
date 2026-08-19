# S-DBG Technical Design

## 1. Design Status

| 项目 | 状态 |
| --- | --- |
| Slice | `S-DBG` |
| Integration Contract | `IC-SDBG-RESET@0.1` |
| 数据访问 | `DebugResetRepository` |
| 用例编排 | `DebugResetService` |
| 环境开关 | `DEBUG_RESET_ENABLED`，默认关闭 |

## 2. API

`POST /api/v1/debug/reset/current-account` 使用 Bearer 身份上下文，不接收请求体。成功响应使用统一 `{code, msg, data}` 包络；错误由统一异常处理器映射为 401、403、409 或 500。

## 3. Transaction and Storage

Repository 锁定当前 Candidate 或 HrProfile，检查其资源关联的 `AsyncTaskRun` 是否处于 `queued/running`，然后在一个数据库事务中删除业务记录和终态任务记录。HR 重置按外键约束顺序删除岗位产生的 `ProgressEvent`、`Application`、`Match`、岗位解析快照和 `Job`；候选人拥有的 `AgentRunContext`、`JobGoal` 和候选人资料不属于 HR 清理范围。

不再被 Resume、CandidateDocument 或 Job 引用的 `StoredFileObject` 标记为 `deleting`。事务提交后删除物理对象并最终确认数据库记录；物理删除失败时保留 `deleting` 状态，交由对象清理调度重试。

## 4. Layer Boundaries

- API 只负责身份依赖、统一响应和错误映射；
- Service 负责开关、事务编排、对象清理和安全日志；
- Repository 负责归属查询、活动任务检查、删除和引用判断；
- Object Storage 只处理已授权的存储键。

## 5. Readiness / Verify

Readiness 需要确认 PostgreSQL、对象存储目录和后端服务可用。真实联调步骤和开发者演示结果见 Integration Scenario；Scenario 第 4 节由开发者填写，coding Agent 不代填。
