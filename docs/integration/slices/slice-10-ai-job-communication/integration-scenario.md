# Integration Scenario：S10-01 简历事实问答

> Scenario ID：`IS-S10-01`
> 关联 Slice：S10 AI 求职沟通
> Integration Contract：[`IC-S10-AI-COMMUNICATION@0.4`](./integration-contract.md)
> 场景类型：`frontend_visible + capability_acceptance`
> 交付状态：`integration_delivered`（本场景为 S10-01；S10-02、S10-03 由独立 Scenario 交付）

> 依赖交付：`APPLICATION-CONVERSATION@0.1` 已由 S-08 生产并完成开发者前后端联调复验；本场景只消费该交接，不重新定义 Conversation 初始化责任。

## 1. 交付目标

在 S-08 已完成岗位匹配并初始化当前 Application Conversation 的前提下，当前只验收 S10-01 简历事实问答：

```text
HR 简历问题 → Agent 基于绑定 Resume 回答
```

## 2. 前置条件与演示数据

- 已登录受控 HR 身份，且服务端确认其对当前 Job、Candidate、Application 和 Conversation 有权访问；
- S-08 已完成岗位匹配并创建当前 Application；
- 当前投递存在 S-07 启动时绑定的 Resume、CandidateProfile、JobGoal 和结构化 JD；
- 当前 Application 已由 S-08 幂等初始化唯一 Conversation 容器且不含欢迎消息；
- 使用固定脱敏 Resume/CandidateProfile Fixture；
- Capability Acceptance 使用可替换 Qwen Transport；真实 Qwen 调用由外部能力证据记录；
- 自动验收命令（从 `careerpass-backend` 执行）：`uv run pytest tests/acceptance/s10_01_communication -m capability_acceptance -o addopts='-q'`；
- Acceptance Artifact：`tests/acceptance/s10_01_communication/artifacts/report.md` 和 `actual.json`。

依赖场景：S-07、S-08 已通过的交付结果；其中 `APPLICATION-CONVERSATION@0.1` 已完成联调复验。

## 3. 演示条目与预期结果

| 条目 | 操作 | 预期系统结果 | 预期页面结果或验收产物 |
| --- | --- | --- | --- |
| S10-01 | HR 在当前 Conversation 询问候选人的经历、项目或技能 | Agent 读取 S-07 绑定 Resume，生成直接事实支持的正式消息 | HR 看到回答；不看到 Resume 原文或证据摘要 |
| S10-02 | 独立资料附件场景 | 已由 `IS-S10-02` 完成交付 | 不属于当前 S10-01 关闭条件 |
| S10-03 | 独立主动沟通场景 | 已由 `IS-S10-03` 交付 | 不属于当前 S10-01 关闭条件 |

## 4. 验收边界

- 验收 S10-01 Agent Turn 是否经过上下文授权、结构化校验、业务校验和幂等写入；
- 验收 S10-01 的事实来源优先级和回答可见性；
- 验收有事实回答、经历范围内的否定回答、资料范围不足模板、Qwen 失败、越权、跨 Application 隔离和敏感信息不泄露；
- S10-02 附件、S10-03 query、Application 状态变化、真实外部沟通和生产级实时推送不属于本次验收。

## 5. 最小演示验证结果

> 只能由开发者在真实 Capability Acceptance 完成后填写。Coding Agent 不代填实际结果或证据。

| 步骤 | 操作 | 实际结果 | 其它问题 |
| --- | --- | --- | --- |
| S08→S10 Handoff | S-08 成功创建 Application 后，HR 进入沟通页读取当前会话 | 已通过前后端联调；唯一 `conversation_id` 可返回，首次消息列表为空，未生成欢迎消息 | 无 |
| S10-01 | HR 登录后进入真实沟通页，在空会话中询问“你的工作经历中有包括大模型训练吗？”并发送 | 当绑定 Resume-derived 经历事实已覆盖工作/项目范围且未出现训练相关事实时，Agent 明确回答没有大模型训练相关经历，并可安全展开说明已记录的下游应用经历；安全投影仅含消息主体、正文和时间 | 无 |
| S10-01 | HR 在同一会话询问“请介绍候选人的技能。” | 已通过真实前后端路径；页面显示 Agent 基于当前投递 Resume-derived facts 的正式回答 | 无 |
| S10-01 | 在同一会话询问“候选人的出生地是什么？” | 已显示固定受控模板“暂时无法从当前求职资料确认这个问题。” | 无 |
| S10-01 | 重复提交同一 `client_message_id`，并执行并发重复请求 | PostgreSQL 集成测试确认只保留一条 HR Message、一条 AgentTurn 和一条 Agent Message；重复请求复用原结果 | 无 |
| S10-01 | 检查页面和响应字段 | 未发现 Resume 原文、fact_refs、Prompt、模型原始响应、联系方式、文件路径或内部对象定位 | 无 |
| S10-02 | 独立资料附件场景不在本场景执行 | 已由独立 Scenario 完成关闭 | `IS-S10-02 integration_delivered` |
| S10-03 | 独立场景不在本次执行 | 已由独立 Scenario 完成关闭 | `IS-S10-03 integration_delivered` |

## 6. 问题与整改

| 记录编号 | 问题类型 | 原因与分析 | 整改结果 | 验收结果 |
| --- | --- | --- | --- | --- |
| S10-01-001 | 并发重复请求读取到会话内缓存的 `processing` 状态 | 同一 SQLAlchemy Session 未刷新已提交 AgentTurn | Repository 查询启用 `populate_existing`，并增加有限等待后复用已完成结果 | 已通过 PostgreSQL 并发集成测试 |
| S10-01-002 | 首次 Compose 后端未加载 Qwen Key | 隔离容器启动时未继承当前运行环境配置 | 重新创建 backend 容器并完成真实 Qwen 前端复验；不在日志或 Artifact 中记录密钥 | 已通过 |
| S10-01-003 | “没有相关经历”被错误归入“无法确认” | Agent Prompt 和 Service 只区分 supported/unsupported，没有表达已覆盖经历范围内的否定事实 | 对“大模型训练”存在性问题增加受控否定回答：经历事实充分且无训练相关事实时返回“没有大模型训练相关经历”；资料范围不足仍返回原受控模板 | 已通过单元测试和 PostgreSQL 集成测试 |

## 7. 关闭结论

- 最小演示步骤通过：`是`；
- Acceptance Artifact 已生成并由开发者审阅：`是`；
- Contract、后端实现和实际消息结果一致：`是`；
- 最终结论：开发者裁定 S10-01 交付完成，状态为 `integration_delivered`；S10-02 已由独立 `IS-S10-02` 完成交付，S10-03 已由独立 `IS-S10-03` 完成交付，三个 Scenario 均为 `integration_delivered`。本文件仍只关闭 S10-01。
