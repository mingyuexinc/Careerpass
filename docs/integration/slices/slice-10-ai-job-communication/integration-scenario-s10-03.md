# Integration Scenario：S10-03 主动补齐岗位信息并进行求职目标判断

## 1. 基本信息

| 字段 | 内容 |
| --- | --- |
| Scenario ID | `IS-S10-03` |
| Slice | S10 AI 求职沟通 |
| Contract | `IC-S10-AI-COMMUNICATION@0.5` |
| 类型 | `frontend_visible` |
| 测试层 | Capability Acceptance、Slice Integration、Cross-Slice Integration、E2E、安全测试 |
| 当前状态 | `integration_delivered` |

## 2. 场景目标

HR 进入当前 Application Conversation 后，系统自动检查当前 JobGoal 与结构化 JD 的缺口；有且仅有一个可确认条件时发送唯一 query，读取其后 HR 消息的明确二元答案，并发送固定继续或停止回复。没有条件、没有有效回答、解析失败和重复触发均不产生额外错误提示；Application、Match 和投递状态不变。

## 3. 固定 Fixture

Fixture 必须包含一个 HR、Candidate、Job、Application、Conversation、当前 active JobGoal、已解析 JD 和一个当前匹配阶段未处理且 JD 无法确认的过滤条件。默认演示条件为“不考虑外包岗位”，但测试数据应允许替换为其它 JobGoal 条件。

回答样本至少覆盖：`是`、`不是`、`对`、`不对`、`属于外包岗位`、`不属于外包岗位`、带额外说明的明确答案、无回复、无法识别二元答案后再发送明确答案，以及重复进入同一 Conversation。另准备一个 JD 已明确条件的静默 Fixture。

固定验收目录：

```text
careerpass-backend/tests/acceptance/test_s10_03_goal_communication_capability.py
docs/integration/slices/slice-10-ai-job-communication/artifacts/IS-S10-03-acceptance/
  expected.json
  actual.json
  report.md
```

能力验收命令：

```text
cd careerpass-backend
uv run pytest tests/acceptance/test_s10_03_goal_communication_capability.py -m capability_acceptance -q
```

真实联调使用后端统一启动门禁、前端代理入口和受控账号；输出只允许记录关联 ID、场景、轮次、状态、结果分类和消息数量，不记录简历原文、JobGoal 原文、模型原始响应、令牌、路径或对象键。

## 4. 验收步骤与预期结果

| 步骤 | 操作 | 预期结果 |
| --- | --- | --- |
| 1 | HR 打开当前 Conversation | 前端调用主动触发接口；服务端通过 HR→Job→Application→Conversation 归属校验 |
| 2 | 读取有缺口 Fixture 的会话 | 追加一条唯一 Agent query，AgentTurn 为 `goal_query/waiting/query_sent` |
| 3 | 重复进入同一 Conversation | 返回已有 query，不新增 Message 或 AgentTurn |
| 4 | HR 不回复 | 不追问，query 保持待处理 |
| 5 | HR 回复无法识别的内容 | 不追加 Agent 提示，当前判断保持 pending |
| 6 | HR 后续回复明确二元答案 | 将该消息视为原 query 的回答，追加固定“好的，了解”或“感谢沟通，当前不考虑这个岗位了” |
| 7 | HR 使用同义二元表述并带额外说明 | 只提取明确二元答案；混合肯定/否定仍 pending |
| 8 | 打开无条件 Fixture | 静默结束，不创建 AgentTurn，不发送消息 |
| 9 | 检查 Application、Match 和投递状态 | 与触发前完全一致 |
| 10 | 使用其它 HR、Candidate、Application 或 Conversation ID | 返回安全的 403/404，不泄露资源详情 |

## 5. 开发者实际结果

2026-08-21，开发者重启后端并在前端完成 S10-03 场景复测，全部步骤通过。脱敏结果记录于 [`artifacts/IS-S10-03-acceptance/report.md`](artifacts/IS-S10-03-acceptance/report.md) 和 [`actual.json`](artifacts/IS-S10-03-acceptance/actual.json)。运行数据库迁移版本为 `20260821_0017`。

| 验收项 | 实际结果 |
| --- | --- |
| 有缺口时主动提问 | 通过；进入当前 Conversation 后发送唯一 query，AgentTurn 为 `goal_query/waiting/query_sent` |
| 无可提问条件 | 通过；静默结束，不创建 AgentTurn，不发送消息 |
| 未回答与解析失败 | 通过；不追问、不发送额外提示，保持待处理 |
| 后续明确二元回答 | 通过；可继续完成原 query，并发送固定继续/停止回复 |
| 二元表达与额外说明 | 通过；支持约定表述，混合或不明确回答保持待处理 |
| 重复触发 | 通过；同一 Conversation 复用既有结果，不重复追加 query |
| 状态与权限隔离 | 通过；Application、Match 和投递状态不变，归属校验有效 |

本次整改记录：

- `S10-03-001`：运行数据库未应用 `20260821_0017`，主动接口返回 404；已执行迁移并重建后端容器。
- `S10-03-002`：主动 query 已写入但响应投影读取未预加载的 `Message.attachments`，返回 500；已修复主动 query 的空附件投影并增加回归测试。

## 6. 问题整改与关闭

问题记录至少包含：问题编号、复现步骤、预期/实际、影响范围、根因、整改提交、回归命令和最终结果。上述成功、静默、等待、解析失败、后续有效回答、重复触发、权限隔离和状态不变均已通过，`IS-S10-03` 标记为 `integration_delivered`，S10-3 Verify/Close 完成。
