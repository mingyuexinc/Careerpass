# Integration Scenario：IS-S09-01 HR 更新投递进度

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `IS-S09-01` |
| 名称 | HR 恢复岗位并查看、更新单条投递进度 |
| 关联 Slice | S-09 投递进度更新 |
| Integration Contract | [`IC-S09-APPLICATION-PROGRESS@0.1`](integration-contract.md) |
| 场景类型 | `frontend_visible` |
| 内部能力测试层 | `E2E` / `Cross-Slice` |
| 交付状态 | `integration_delivered` |

## 1. 交付目标

```text
HR 上传 JD → Candidate 匹配形成投递 → HR 重新登录恢复岗位和投递 → 查看四项投递信息 → 更新 submitted 为 screening
→ 后端追加 ProgressEvent → 求职者刷新进度页看到 screening
```

## 2. 前置条件与演示数据

- 已有通过 S-01 的 HR 和 Candidate 受控演示身份；
- S-08 已创建当前首轮 Application，至少一条记录状态为 `submitted`；
- 至少存在一个未删除、属于当前 HR 的 Job；
- 求职者侧可读取同一 Application；
- HR 重新登录后岗位查询和投递查询均可返回同一业务数据；
- 需要覆盖一条 Offer 达标数据，使 AgentRun 可进入 `finished/offer_target_reached`；
- 自动化验证使用隔离 Compose PostgreSQL 和当前前端测试入口；本 Slice 不引入外部投递或实时推送。

## 3. 演示步骤与预期结果

| 步骤 | 操作 | 预期系统结果 | 预期页面结果或验收产物 |
| --- | --- | --- | --- |
| 1 | HR 上传 JD；Candidate 匹配并形成投递；HR 退出后重新登录 | 岗位和投递仍保存在数据库并按 HR 归属可查询，岗位上传卡片保留原始文件名 | 岗位页和投递进度页恢复数据，文件名不被岗位解析标题替代 |
| 2 | 查看投递列表 | 返回当前 HR 当前首轮 Application | 页面只展示岗位名称、公司名称、候选人姓名和当前投递进度 |
| 3 | 将 `submitted` 更新为 `screening` | 校验合法迁移，更新 Application，追加 `application_status_updated` 事件 | 当前记录刷新为“初筛中” |
| 4 | 求职者刷新进度页 | 返回同一 Application 的最新状态 | 求职者看到“初筛中” |
| 5 | 尝试回退、修改终态或访问无权记录 | 返回业务失败且不改变原状态 | 页面保留原状态并显示失败反馈 |
| 6 | 无 Application 时进入页面 | 返回空列表 | 页面展示“暂无投递记录”空状态 |
| 7 | 将一条记录更新为 `offer` 并达到目标 | 同事务结束 AgentRun、标记 JobGoal `achieved` | Agent 显示已结束，其他未终态记录仍可更新 |

## 4. 最小演示验证结果

> 仅由开发者在真实前端和后端联调后填写。

| 步骤 | 操作 | 实际结果 | 其它问题 |
| --- | --- | --- | --- |
| 1–2 | HR 跨角色恢复、投影查询与页面渲染 | 通过：HR Job 与 HR Application 独立查询均按当前 HR 归属返回，岗位卡片保留原始 JD 文件名，前端恢复岗位和投递；投影不含敏感候选人字段 | `tests/integration/test_s09_application_progress.py`、`hrJobApi.test.ts`、`workspaceStore.test.ts`、前端页面测试 |
| 3–4 | `submitted → screening` 与候选人读取 | Application、ProgressEvent 和候选人侧查询结果均为最新状态 | PostgreSQL 集成测试、既有 S-08 查询链路 |
| 5–7 | 回退/终态/空状态/Offer 达标 | 通过：非法变更失败；终态禁用；Offer 达标结束 AgentRun、达成 JobGoal，其它记录仍可更新 | S-09 后端单测、前端测试、PostgreSQL 集成测试 |

## 5. 问题与整改

| 记录编号 | 问题类型 | 原因与分析 | 整改结果 | 验收结果 |
| --- | --- | --- | --- | --- |
| S09-01 | 浏览器控制连接受信路径校验未建立 | 本轮未通过浏览器工具完成人工点击演示 | 采用前端组件/API 自动断言和隔离 PostgreSQL 真实事务链路完成验证 | 不影响自动化交付结论 |
| S09-02 | HR 重登后岗位页为空 | JobsPage 只保留页面局部上传结果，工作区刷新未读取 Job；角色切换未清理并强制刷新工作区 | 新增 `GET /api/v1/jobs/hr/current`、独立 `HrJob` 投影、HR 岗位/投递双查询刷新和角色切换清理 | 通过自动化前端测试、真实 PostgreSQL 归属查询和容器健康检查 |
| S09-03 | HR 投递列表包含历史 Candidate 的重复岗位 | HR Application 查询把历史 Candidate 的 AgentRun 误纳入当前单 Candidate 演示；当前数据库表现为 5 条最新投递外加历史 Candidate 的旧 006 投递 | “当前首轮”改为取全局最新 `AgentRunContext`；历史运行不再进入 HR 查询和状态更新范围 | 已验证：HR 查询由 6 条降为 5 条，001、002、003、004、006 各 1 条；S-09 PostgreSQL 集成测试通过 |
| S09-04 | HR 重登后岗位卡片显示岗位标题而非原始文件名 | `Job` 未持久化上传文件名，HR Job 查询和前端只能使用解析后的岗位标题 | 新增 `jobs.file_name`、HR Job 查询字段和前端 `HrJob.fileName` 映射；新上传岗位优先展示原始文件名，历史记录安全回退 | 开发者前后端联调复测通过；数据库迁移、后端接口、前端页面和回归测试通过 |

## 6. 关闭结论

- 最小演示步骤通过：`是`
- 跨角色岗位恢复步骤通过：是（原始 JD 文件名、岗位和投递均可恢复）
- S-09 完整流程通过：是（HR 登录/上传/恢复/查看/更新，求职者刷新读取最新进度，非法回退、终态、空状态、权限和 Offer 达标联动均已复测）
- 问题已整改并完成回归：`是`
- 前端 Mock、真实 API 和页面结果一致：`是`
- 最终结论：`integration_delivered`；S-09 交付目标达成
