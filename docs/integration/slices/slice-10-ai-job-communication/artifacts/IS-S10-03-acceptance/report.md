# IS-S10-03 开发者联调验收报告

## 结果

- 验收日期：2026-08-21
- Scenario：`IS-S10-03`
- Contract：`IC-S10-AI-COMMUNICATION@0.5`
- 结论：通过，`integration_delivered`
- 运行数据库迁移：`20260821_0017`

## 脱敏验收证据

| 项目 | 结果 |
| --- | --- |
| 当前 Conversation 自动触发唯一 query | 通过；`goal_query/waiting/query_sent` |
| 无条件静默 | 通过；无 AgentTurn、无消息 |
| 未回答/解析失败 | 通过；无追问、无额外提示，保持 `pending` |
| 后续明确二元回答 | 通过；完成原 query 并发送固定继续或停止回复 |
| 常见二元表达和额外说明 | 通过；混合或不明确回答不作判断 |
| 重复进入/重复触发 | 通过；不重复追加 query，复用同一 AgentTurn |
| Application、Match、投递状态 | 通过；状态不变化 |
| 归属与跨资源隔离 | 通过；返回安全的资源不可用结果 |

## 整改记录

1. 运行数据库未应用 `20260821_0017` 导致主动接口 404；已执行迁移并重建后端。
2. 主动 query 响应投影触发 `Message.attachments` 的 `lazy="raise"` 导致 500；已改为主动 query 显式返回空附件集合，并增加回归测试。

## 回归结果

- S10-03 Capability Acceptance：13 passed。
- 前端 `npm run typecheck`：通过。
- 前端 `conversationsPage.test.tsx`：1 passed。
- 受控运行时主动 query：HTTP 200，消息数量 1，重复触发未新增 query。
