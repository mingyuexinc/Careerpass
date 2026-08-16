# S-DBG 一键恢复当前账号初始状态

## Goal

在开发/联调环境中，已登录的候选人或 HR 可以清理当前账号产生的业务数据和临时对象，并自动回到登录页。

## Preconditions

- 当前用户已通过 S-01 登录并拥有有效的 Candidate 或 HrProfile 身份；
- 后端显式开启 `DEBUG_RESET_ENABLED`；
- 当前账号没有排队中或运行中的异步任务。

## Business Rules

- 重置范围只包含当前登录身份拥有的资源，不接受客户端提交账号或资源 ID；
- 保留 User、Candidate/HrProfile、角色关系和受控演示账号；
- 候选人清理简历、画像、附加资料、当前求职目标及相关任务；
- HR 清理岗位、岗位解析快照及相关任务；
- 对象文件仅在不再被其他资源引用时进入删除流程；
- 存在活动任务时整体拒绝，不产生部分删除；
- 重复调用幂等；
- 生产环境不可开启该能力。

## Scope / Non-goals

包含当前已实现资源的账号级清理、对象文件清理和前端自动退出登录。

不包含全库重置、其他账号数据清理、账号删除、Redis 全局清空或生产数据恢复。

## Acceptance Criteria

- 候选人和 HR 使用各自按钮均能清理当前账号数据；
- 其他账号和演示账号身份保持不变；
- 活动任务返回冲突错误且数据库不发生部分删除；
- 成功后前端清空本地工作区并跳转登录页；
- 关闭环境开关后接口不可用且页面按钮不显示。

## Integration

- Integration Contract：[`../../../../../docs/integration/slices/slice-debug-reset/integration-contract.md`](../../../../../docs/integration/slices/slice-debug-reset/integration-contract.md)
- Integration Scenario：[`../../../../../docs/integration/slices/slice-debug-reset/integration-scenario.md`](../../../../../docs/integration/slices/slice-debug-reset/integration-scenario.md)
