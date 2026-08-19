# S-09 投递进度更新切片规格

> 本 Slice 关联 [`IS-S09-01`](../../../../../docs/integration/slices/slice-09-application-progress-update/integration-scenario.md) 和 [`IC-S09-APPLICATION-PROGRESS@0.1`](../../../../../docs/integration/slices/slice-09-application-progress-update/integration-contract.md)。
>
> 当前阶段：`Close` 完成；代码、自动化验证和 Integration Scenario 已交付，`IS-S09-01` 标记为 `integration_delivered`。

## 1. 目标

HR 登录后进入投递进度管理页，查看当前 HR 有权访问的首轮 Application，并更新单条 Application 的合法招聘阶段；求职者刷新后看到对应进度变化。

岗位上传后的跨角色恢复也属于本 Slice 的读取闭环：HR 重新登录或重新进入工作区后，仍可读取本人未删除的岗位和对应投递；这不改变 S-02 的上传语义。

## 2. 输入

- 已登录 HR 发起的查询或单条状态更新请求；
- 状态更新请求中的目标 Application 和目标后续进度；
- S-08 已形成的当前首轮 Application、Job、CandidateProfile、AgentRunContext 和 JobGoal 业务资源。

## 3. 输出

- HR 查询当前 HR 所有未删除岗位下的当前首轮 Application；
- HR 页面只展示岗位名称、公司名称、候选人姓名和当前投递进度；
- 合法更新写入 Application 当前状态和一条 `application_status_updated` ProgressEvent；
- Application 进入 `offer` 后，达到 `offer_target` 时 AgentRun 结束并将 JobGoal 标记为 `achieved`；
- AgentRun 结束后，其它未终态 Application 仍可继续推进。

## 4. 前置条件

- 当前请求已通过 S-01 认证，活动角色为 HR，并具有 `HrProfile`；
- Application 关联一个 Candidate、Job、Match 和 AgentRunContext；
- Job 未删除且归属于当前 HR；
- 当前演示只包含一个 HR 业务身份和一个 Candidate 业务身份；
- S-08 已为当前首轮 Application 写入初始 `submitted` ProgressEvent。

## 5. 业务规则

本 Slice 应用业务基线事实：`BF-RULE-039` 至 `BF-RULE-044`、`BF-STATE-005` 至 `BF-STATE-008`。

### 5.1 查询范围和展示边界

- 只查询当前 HR 所有未删除 Job 下、当前首轮 AgentRun 的 Application；
- 工作区恢复查询当前 HR 所有未删除 Job；岗位投影提供上传时的原始文件名、岗位名称、公司名称、创建时间和解析任务状态；
- 不支持多 Candidate、多轮投递、历史轮次、跨 HR 查询或独立岗位授权配置；
- `application_id`、`job_id` 等内部标识仅用于接口操作，不作为页面业务信息展示；
- 不返回联系方式、简历原文、匹配分数、推荐理由、沟通全文或其它候选人资料；
- Candidate 姓名取已校验 CandidateProfile 的 `full_name`；公司名称取结构化 JD 快照的 `company_name`。

### 5.2 状态迁移

状态集合为：`submitted`、`screening`、`written_test`、`interview_1`、`interview_2`、`interview_3`、`hr_interview`、`offer`、`terminated`。

- 非终态可以直接推进到任一后续阶段，也可以进入 `terminated`；
- 不允许回退到更早阶段；
- `offer` 和 `terminated` 为终态，进入后不可修改；
- 更新为当前状态按幂等成功处理，不新增 ProgressEvent；
- 非法状态、非法回退和终态修改失败，原状态保持不变。

### 5.3 Offer 联动

- Application 进入 `offer` 后统计当前首轮 AgentRun 的 Offer 数量；
- Offer 数量达到 `offer_target` 时，在同一事务内：
  - AgentRun 更新为 `finished`；
  - `finish_reason` 更新为 `offer_target_reached`；
  - 当前 JobGoal 更新为 `achieved`；
- AgentRun 结束后不可重新启动，但其它未终态 Application 仍可按状态机推进。

## 6. 范围 / 非目标

### 当前范围

本 Slice 包含 HR Application 查询、单条状态更新、权限校验、状态机、ProgressEvent 和 Offer 达标联动。

### 非目标 / 延期

本 Slice 不包含沟通会话或消息、简历和附加资料展示、匹配结果展示、真实外部投递、多轮投递、实时推送、HR 修改候选人或岗位全局状态，以及新增业务实体。

沟通页面继续属于 S-10；本 Slice 不实现 Conversation/Message 实体、接口、消息发送或 Agent 回复生成，也不以沟通记录作为 S-09 的验收条件。

## 7. 技术约束

- 必须复用现有 `Application`、`ProgressEvent`、`Job`、`CandidateProfile`、`AgentRunContext` 和 `JobGoal`；
- MVP 不新增业务实体或业务表；岗位恢复闭环新增 `jobs.file_name` 上传元数据字段，并由 Alembic `20260819_0014` 迁移落地；Application 状态更新不新增字段；
- 所有接口响应遵循 `{code, msg, data}`；
- 数据访问必须经过 Repository，HR → Job → Application → Candidate 的归属校验不得下沉为前端逻辑；
- 状态更新、ProgressEvent、Offer 统计、AgentRun 和 JobGoal 联动必须保持同一事务；
- 本 Slice 不产生异步任务、LLM 调用、真实外部投递或消息副作用。

## 8. 验收标准

- HR 能进入投递进度页，并只看到岗位名称、公司名称、候选人姓名和当前投递进度；
- HR 退出并重新登录后，岗位页仍能恢复本人未删除岗位，投递进度页仍能恢复对应投递；
- HR 退出并重新登录后，岗位 JD 上传卡片仍展示新上传岗位的原始文件名，不以解析后的岗位名称替代；
- HR 只能查询当前 HR 所有未删除岗位下的当前首轮 Application；
- HR 可将一条非终态 Application 更新到合法后续阶段或 `terminated`；
- 同状态重复提交幂等成功且不新增 ProgressEvent；非法回退、终态修改和无权访问失败，原状态保持不变；
- 有效状态变化写入一条带前后状态、`actor=hr` 和服务端时间的 `application_status_updated` ProgressEvent；
- Offer 达标时 AgentRun 结束、JobGoal 达成，且其它未终态 Application 仍可继续更新；
- 求职者刷新或重新进入页面后可看到最新进度；
- 无投递记录时显示空状态，查询或更新失败时显示安全失败反馈，页面不泄露敏感候选人资料。

## 8.1 交付场景

| 项目 | 内容 |
| --- | --- |
| Integration Scenario | [`IS-S09-01`](../../../../../docs/integration/slices/slice-09-application-progress-update/integration-scenario.md) |
| Integration Contract | [`IC-S09-APPLICATION-PROGRESS@0.1`](../../../../../docs/integration/slices/slice-09-application-progress-update/integration-contract.md) |
| 开发者演示目标 | 受控 HR 登录后恢复岗位和投递、查看四项投递信息、推进状态；求职者刷新确认变化；演示非法回退、终态、空状态和 Offer 达标联动。 |
| 场景关闭条件 | 完成真实前后端演示、自测、问题整改和回归；实际结果只填写在 Integration Scenario。 |

## 9. 开发者需裁决事项

无。S-09 的业务范围、展示字段、状态、权限、Offer 达标联动和术语均已完成裁决。

## 10. Gate、完成标准与回退

| Gate | 进入条件 | 结果 |
| --- | --- | --- |
| Slice Select | S-08 已交付，S-09 依赖和业务裁决已确认 | `passed` |
| Slice Design | 本规格、Technical Design、Contract 和 Scenario 一致 | `passed` |
| Readiness Check | 现有表、身份、演示数据、测试入口和错误边界已核对 | `passed` |
| Implement | 仅在 Readiness Check 通过后进入 | `passed` |
| Verify | 真实数据库状态事件、Offer 联动、前端投影和错误边界通过 | `passed` |
| Close | Scenario 实际结果已填写并完成回归 | `passed` |

当前 Slice 已完成 Slice Select、Slice Design、Readiness Check、Implement、Verify 和 Close。

完成标准：HR 可按岗位查看四项业务信息；可更新一条合法后续状态；非法更新不改变原状态；ProgressEvent 与状态一致；Offer 达标联动正确；求职者刷新后看到最新状态；不泄露未授权或敏感信息。

若发现 API 字段、状态迁移、资源归属、事务责任、跨端可观察结果或场景无法闭合，分别回退到 Technical Design、领域/数据设计、Slice Design、Readiness Check 或 Integration Scenario 对应阶段，禁止通过前端临时逻辑或扩大权限绕过。
