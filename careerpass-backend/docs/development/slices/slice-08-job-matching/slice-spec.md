# Slice：S-08 岗位匹配与投递

> 本 Slice 关联 [`IS-S08-01`](../../../../../docs/integration/slices/slice-08-job-matching/integration-scenario.md) 和 [`IC-S08-JOB-MATCHING@0.1`](../../../../../docs/integration/slices/slice-08-job-matching/integration-contract.md)。
>
> 当前阶段：Close 完成，S-08 已交付；`IS-S08-01` 已通过开发者复测并标记为 `integration_delivered`。

## 1. 目标

S-07 启动事务提交后，后端同步执行首轮岗位筛选、Match 持久化和通过筛选岗位的系统内投递。候选人在求职进度页查看已创建的 Application、推荐匹配得分和推荐理由。

## 2. 输入

- S-07 已创建且属于当前 Candidate 的 `AgentRunContext`；
- 启动时绑定的候选人画像和简历业务语义摘要；
- 启动时保存的求职目标快照；
- 关联 HR 上传、未删除、解析成功且具备五项核心字段的结构化 JD；
- 当前演示岗位池最多 20 个。

S-08 不读取 JD 或简历原文，不消费公司简介、优先条件、加分项和其他非核心 JD 内容。

## 3. 输出

- 每个可用岗位最多生成一条 `Match`；
- `Match` 独立保存算法版本、输入快照、筛选状态、评分和推荐理由；
- 通过投递筛选的 Match 创建一条初始状态为 `submitted` 的 `Application`；
- Application 创建时记录初始 `ProgressEvent`；
- Application 成功创建后，幂等初始化一个当前 Conversation 容器，供 S10 使用；不写入欢迎消息；
- 候选人进度查询只返回 Application，不返回未形成投递记录的 Match；
- 全部可用岗位筛选完成且本轮 Application 数量为 0 时，AgentRun 进入 `finished`，结束原因是 `no_match`。

## 4. 业务规则

完整业务规则以项目级业务基线和 [S-08 v0.1 匹配算法](../../../../../docs/business/matching/matching-algorithm-v0.1.md) 为准。本 Slice 只锁定执行边界：

- S-08 由 S-07 启动链路内部同步调用，前端不提交匹配命令；
- 当前 Candidate 使用关联 HR 的全部可用结构化 JD，逐个筛选，不采用 Top-N 投递；
- 同一 `run_id + job_id` 只能处理一次；重复启动或重入不得重复生成 Match/Application；
- `offer_target` 不限制筛选数量和投递数量；
- 三个评分维度独立计算，但允许通过加权总分补偿；
- 推荐理由使用确定性规则模板，不依赖大模型；
- 不实现真实外部投递、异步匹配、算法升级和匹配失败业务分支。

## 5. 数据与状态边界

### 5.1 Match

Match 必须绑定 Candidate、Job 和 AgentRunContext，并保存：

- `algorithm_version`；
- 已脱敏的 JD、候选人和目标业务语义输入快照；
- `filtered_out`、`not_matched`、`matched` 或 `application_created` 状态；
- 岗位画像、能力层级、技能匹配和总分；
- 推荐理由和过滤/未匹配原因。

唯一约束为 `UNIQUE(run_id, job_id)`。

### 5.2 Application

Application 必须绑定 Candidate、Job、AgentRunContext 和通过筛选的 Match。创建时状态为 `submitted`，并记录初始 ProgressEvent。S-09 后续负责投递状态推进，本 Slice 不实现 HR 状态修改。

唯一约束为 `UNIQUE(run_id, job_id)`；一条 Application 只能关联一条 Match。

## 6. 范围与非目标

### 当前范围

- 读取结构化 JD、候选人画像和求职目标快照；
- 执行 v0.1 过滤、匹配、评分和推荐理由生成；
- 持久化 Match；
- 创建 Application 和初始 ProgressEvent；
- 同步更新 AgentRun 完成原因；
- 提供候选人 Application 查询。

### 非目标

- 不新增前端匹配命令；
- 不公开查询未投递 Match；
- 不实现真实招聘平台投递；
- 不实现多轮投递、算法升级、向量召回、重排序或 LLM 匹配；
- 不实现 S-09 的 HR 投递状态更新和完整进度事件管理；
- 不处理无可用 JD、匹配任务失败或 Application 创建失败的用户业务分支。

## 7. 验收标准

- 多个可用岗位按顺序完成筛选，每个岗位最多一条 Match；
- 用户硬过滤命中的岗位保存为 `filtered_out`；
- 评分未达阈值的岗位保存为 `not_matched`；
- 通过筛选的岗位创建 Application，进度页展示得分和推荐理由；
- 仅有 Match、没有 Application 的岗位不出现在进度页；
- 所有岗位均未创建 Application 时，AgentRun 以 `no_match` 结束并展示“当前没有可供匹配的岗位”；
- 重复启动或重入不产生重复 Match/Application；
- 岗位池为 20 个时仍使用同步路径完成；
- `offer_target` 改变不改变本轮岗位筛选数量上限。

## 8. Gate 结果

| Gate | 结果 |
| --- | --- |
| Slice Select | 通过：S-08 是首轮匹配和系统内投递的业务结果 Slice |
| Slice Design | 通过：范围、状态、数据和依赖已锁定 |
| Integration Contract | 已锁定：`IC-S08-JOB-MATCHING@0.1` |
| Integration Scenario | 已定义：`IS-S08-01` |
| Readiness Check | 已通过：迁移、参数、测试和依赖边界已确认 |
| Implement | 已完成：Match/Application/ProgressEvent、v0.1、同步编排、查询 API 和前端接入 |
| Verify | 通过：开发者已完成真实 S-08 运行环境复测，前述问题均已整改并通过验收 |
| Close | 完成：`IS-S08-01` 已标记为 `integration_delivered`，S-08 交付完成 |
