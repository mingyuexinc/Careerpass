# 设计

## 模块边界

输入为不可变、额外字段禁止的版本化简历解析请求。简历解析模块负责校验请求指向简历的归属与状态，并通过 Repository 获取受控内容；上游不得传入路径、URL、原文或模型参数。

简历成功路径在同一事务中写入已校验的 `candidate_profiles`、`resumes.parse_status` 和 `async_task_runs.status`。失败路径只写安全失败码和对应终态。岗位 JD 的启动导入与结构化抽取不属于本变更，且不得复用简历表或画像表承载结果。

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
