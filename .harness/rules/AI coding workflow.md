# AI Coding 工作流

## 1. 适用范围

本文件只指导 AI 如何执行前端优先、Slice 层级的编码工作，不定义业务、架构、接口、数据或环境事实。

AI 必须先读取根 AGENTS.md、目标子工程 AGENTS.md 和当前 Slice 相关事实源，再按以下 Gate 串行工作。

## 2. 六阶段 Gate

| Stage | AI 工作 | Gate | 产物 |
| --- | --- | --- | --- |
| Slice Select | 从前端流程和 Slice 计划选择一个业务闭环 | 边界清晰，前置 Slice 已满足 | Slice 标识 |
| Slice Design | 完成 Goal、规则、契约、数据变化、依赖和验收 | 无关键歧义 | slice-spec.md |
| Readiness Check | 核对技术问题、真实外部证据和全局文档同步 | 全部满足或明确 blocked | Ready |
| Implement | 按已批准设计实现完整纵向链路 | 不偏离设计与红线 | 可运行代码 |
| Verify | 验证成功、失败和业务规则 | 既定验收通过 | 测试/验证结果 |
| Close | 对齐文档、实现和证据 | 无遗留阻断项 | Slice Done |

当前 Gate 未通过不得进入下一阶段。已有代码、历史归档、Mock 或任务清单不能替代前置 Gate。

## 3. Slice Select

- 确认 Slice ID、Trigger、唯一主要业务结果、Scope、Non-goals 和稳定结束点。
- 核对上游 Slice 已产生可依赖结果，下游 Handoff 可以明确。
- 若包含第二个可独立验收结果或依赖未定义胶水，保持 blocked。

## 4. Slice Design

只维护一个 slice-spec.md，并补全：

- Goal、用户价值、Trigger 和可观察结果；
- 业务规则、资源归属、权限和敏感信息边界；
- API、异步任务、状态、错误、幂等和数据变化；
- 前置 Slice、Producer、Consumer 和 Handoff Contract；
- 技术方案、外部依赖、失败处理和验收条件。

Producer Slice 的 Handoff Contract 章节是跨 Slice 契约唯一来源，Consumer 只引用相同 ID 和版本。不得在 .harness 建立契约注册表。

## 5. Readiness Check

- 确认设计不存在影响实现的未决范围、授权、接口、数据或状态问题。
- 首次使用的 LLM、第三方 API、队列或其他关键依赖必须有最小真实证据。
- 影响实现的领域、数据、架构和外部能力事实已同步到对应子工程文档。
- 验收环境、测试数据、Repository 边界、统一响应、状态合法性和安全红线可执行。

任一关键项不满足时标记 blocked，不开始编码。

## 6. Implement

- 只实现通过 Readiness Check 的 Slice。
- 完成入口、Service、Repository、数据、任务和可观察结果的完整链路。
- 资源访问必须校验当前身份和归属。
- LLM 输出必须结构化并经业务校验。
- 任务必须可追踪、幂等并有明确终态。
- 日志、追踪和响应不得暴露凭证、敏感原文、内部路径或模型原始响应。

发现设计变化时停止受影响实现并回退。

## 7. Verify 与 Close

Verify 至少覆盖成功路径、非法输入、资源不存在、无权访问、依赖失败、状态迁移、幂等和数据一致性。Mock 不能替代真实外部证据。

Close 前确认 Slice 文档与最终实现一致、全局事实源已同步、验证可追溯、延期项明确且下游 Handoff 可用。

## 8. 回退

| 变化 | 回退 |
| --- | --- |
| Goal、边界、主要结果或前置 Slice | Slice Select |
| 规则、授权、契约、数据、状态、验收或跨 Slice 责任 | Slice Design |
| 关键依赖、技术路线、真实证据或全局同步 | Readiness Check |
| 不影响设计的实现缺陷 | Implement |
| 不影响设计的验证缺口 | Verify |

AI 不得自行批准 Gate；开发者负责关键范围、授权、副作用和 Gate 结论。
