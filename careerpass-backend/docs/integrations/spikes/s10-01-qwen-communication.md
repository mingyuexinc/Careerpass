# S10-01 Qwen 沟通回答能力验证

## 1. 验证对象

- 能力：Qwen Plus OpenAI-compatible Chat Completions；
- 关联 Slice：S10-01；
- 首次进入关键路径原因：HR 简历相关问题需要生成受约束的系统内 Agent 文本回复；
- 输入边界：仅使用已校验的 Resume-derived 结构化事实，不发送简历原文、文件路径、对象定位或模型历史响应。

## 2. 最小真实调用

- 受控输入：固定脱敏工作经历、项目名称和技能结构化 Fixture；
- 实际调用链：S10-01 Qwen adapter → Qwen Plus → Pydantic `ResumeAnswerDraft`；
- 成功标准：返回合法 JSON、回答只引用输入事实、无证据时返回 `supported=false`；
- 失败和超时标准：映射为 `provider_timeout`、`provider_unavailable` 或 `schema_validation_failed`，消息通道可用时由业务层发送受控模板；
- 脱敏要求：请求、响应、日志和 Artifact 不包含简历原文、凭证、内部定位或模型原始响应。

## 3. 结果

- 状态：`passed`（最小真实调用，2026-08-20）；
- 真实证据：使用脱敏结构化事实调用 Qwen Plus，返回内容通过 `ResumeAnswerDraft` 校验，`supported=true`；仅保留回答长度和事实引用数量等脱敏诊断信息；
- 边界证据：请求未包含简历原文、文件路径或对象定位；本记录不保存 Prompt、模型原始响应、凭证或回答正文；
- 仍需补充：后端统一预检、数据库迁移/权限/幂等集成验证和真实前端演示；这些未完成前，S10-01 不标记为 `integration_delivered`。
