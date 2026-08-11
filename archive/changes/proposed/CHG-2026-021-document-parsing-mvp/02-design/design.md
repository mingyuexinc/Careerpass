# 设计（历史摘要；非权威）

> 本文件保留早期阶段的设计摘要，仅作为历史证据，不得作为当前阶段 3/4/5 的方案依据。当前唯一权威方案为 `03-design/design.md`；跨模块契约唯一来源为 `.harness/contracts/resume-parse-request-v1.yaml`。本文件不再承载另一套触发、任务创建或字段定义。

## 模块边界

输入为不可变、额外字段禁止的版本化简历解析请求。简历解析模块负责校验请求指向简历的归属与状态，并通过 Repository 获取受控内容；上游不得传入路径、URL、原文或模型参数。

历史成功路径描述已由当前权威方案取代：G2 在同一事务中创建或复用 queued `AsyncTaskRun`，G3 只消费既有任务并负责解析、画像和终态。岗位 JD 的启动导入与结构化抽取不属于本变更，且不得复用简历表或画像表承载结果。

## 已有简历分支设计资产

| 资产 | 状态 | 说明 |
| --- | --- | --- |
| `ResumeParseRequestV1` | 已完成 | 版本固定、禁止额外字段的上游契约 |
| `DocumentParsingRepository/Service` | 已完成 | 请求持久化、受控读取、画像查询与终态边界 |
| MinerU MCP 适配器 | 已完成 | 仅接收内存 PDF 字节，受控失败映射 |
| Qwen 画像适配器 | 已完成 | 严格 JSON Schema + Pydantic 校验 |
| `careerpass.resume_parse` Worker | 已完成 | 仅接收任务 ID、租约优先、有限重试 |

## 验收原则

单元替身只用于分支覆盖。真实 Redis、PostgreSQL、Celery Worker、MinerU 和 Qwen 的结果必须分项记录；任一未就绪依赖使对应任务保持 `blocked`，不得以模拟测试或既有预验证替代。
