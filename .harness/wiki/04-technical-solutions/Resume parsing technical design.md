# 简历解析技术方案

> MinerU MCP 的 Client/Server 部署、凭证、传输、工具契约和外部验收以 [MinerU MCP 集成技术方案](MinerU%20MCP%20integration%20technical%20design.md) 为准；本文仅定义简历解析业务链路。

## 1. 定位与边界

本方案是正式简历解析的唯一技术权威来源，适用于 `resumes`。它覆盖 PDF 文本提取、结构化画像生成、Schema 校验、失败映射与验收；异步投递、重试、超时和执行租约以 [异步任务技术方案](Async%20task%20technical%20design.md) 为准，对象读取与临时文件以 [对象存储技术方案](Object%20storage%20technical%20design.md) 为准。

候选人资料准备只处理正式简历。`candidate_documents` 不参与本链路；岗位 JD 的录入和解析属于 HR 侧岗位管理模块，不属于本方案。MVP 只接受可提取机器文本的 PDF 简历；不支持 Markdown 简历、扫描 PDF、OCR、图像文字提取或 PDF 版面识别的质量调优。

## 2. 处理链路与职责

```text
Resume + ready StoredFileObject
  → Repository 授权读取
  → 任务专属临时 PDF
  → MinerU MCP（pipeline）
  → 内存 Markdown
  → Qwen Plus 结构化画像输出
  → Pydantic + 业务规则校验
  → 原子写入 candidate_profiles、任务与 Resume 终态
```

Worker 不接受客户端、Agent 或模型提供的路径、URL、MCP 参数或 Schema。它只按 `resume_id` 经 Repository 校验归属、`parse_status=processing` 和关联对象 `ready` 状态后读取文件。临时文件由 Worker 在受限目录创建，以不透明名称保存；无论成功或失败均立即删除。

## 3. MinerU MCP 调用契约

MVP 采用同机官方 `mineru-open-mcp` stdio Bridge 的 `parse_documents` 工具。Worker 仅能为当前执行租约关联的 `ready` 简历创建任务专属临时 PDF，并将该本地路径作为 `file_sources` 的单一成员传给 Bridge；路径不得由客户端、Agent 或模型提供，也不得返回客户端、持久化到数据库或写入日志、追踪。调用显式传入 `enable_ocr=false`，不启用 OCR。远程 MCP 是条件方案，只有其正式鉴权方式与工具 Schema 经独立验收后才能启用。

调用使用经 `tools/list` 验证的 `file_sources` 契约，并配置 `MINERU_API_TOKEN` 使用正式服务能力；不得将无 Token 的 Flash 模式作为生产路径。单文件只接收 Markdown 结果：适配层将 MCP 的内联 Markdown 或受控输出文件统一读取为内存 `extracted_markdown`，不保存 MinerU JSON、ZIP、输出目录、CDN 地址或中间 Markdown 到业务表。

不启用 OCR。若 PDF 可打开但 MinerU 未提取到有效机器文本，应以 `file_unreadable` 终态失败；有有效文本但无法满足画像的必填 Schema 时，才是 `schema_validation_failed`。

## 4. 画像生成与结构化 Schema

MinerU 仅负责文件文本提取，不调用业务画像 LLM。提取后的 Markdown 由画像链路通过百炼 OpenAI 兼容 `chat/completions` 调用 Qwen Plus，使用 `response_format.type=json_schema` 和由 `ResumeProfileExtractionV1.model_json_schema()` 生成的严格 Schema。普通 JSON 模式不构成字段契约，禁止替代 JSON Schema 约束。模型不得推荐、补全或改写目标职位，也不得输出 Schema 以外字段。输出必须再通过 Pydantic 和下列业务约束，才可与简历、任务终态在同一事务内原子持久化。对本链路而言，画像生成、校验和写入是简历解析成功的必要组成部分：不得出现“解析成功但画像失败”，任一环节未完成均按简历解析失败处理。

Qwen 适配器仅接收内存中的 `extracted_markdown`，使用 `DASHSCOPE_API_KEY` 和显式 `QWEN_BASE_URL`、`QWEN_MODEL`；它不得记录 Prompt、简历 Markdown、令牌、原始 HTTP 响应或供应商异常正文。HTTP 超时映射为 `parser_timeout`，429/5xx 与连接故障映射为 `internal_error`，JSON 解析或 Pydantic/业务规则失败映射为 `schema_validation_failed`。

`ResumeProfileExtractionV1` 是内存调用契约，不新增 `resumes.parse_data`。其持久化目标为 `candidate_profiles`；表字段、长度与约束以 [数据模型](../03-contracts/Data%20model.md) 为准。

画像、简历和任务终态的提交必须由 Repository 在同一事务内完成，并同时锁定 `async_task_runs` 与 `resumes`。终态写入条件必须匹配 `task_run_id`、`resource_id`、`task_type=resume_parse`、`resource_type=resume`、`status=running` 和当前 `execution_token`；不匹配的迟到或重复 Worker 返回无副作用结果。成功时原子创建唯一 `candidate_profiles` 记录，将简历置为 `succeeded`、任务置为 `succeeded` 并清除执行租约；失败时不创建画像，将简历与任务同时置为 `failed`，只写受控 `failure_code` 并清除执行租约。

| 字段 | 类型 | 规则与持久化位置 |
| --- | --- | --- |
| `target_job_titles` | `list[str]` | 必填；去首尾空格、去重后至少一个非空项，每项最长 128；写入同名数组字段。 |
| `skills` | `list[Skill]` | 默认空数组；`Skill = {name: str, proficiency: beginner/intermediate/advanced/expert/null}`；写入 JSONB。 |
| `work_experience_summary` | `list[WorkExperience]` | 默认空数组；`WorkExperience = {company_name?, title?, start_date?, end_date?, summary?, highlights: list[str]}`；`start_date` 和 `end_date` 出现时必须为 `YYYY-MM`，未知时为 `null`；写入 JSONB。 |
| `project_experience_summary` | `list[ProjectExperience]` | 默认空数组；`ProjectExperience = {name, role?, summary?, technologies: list[str], highlights: list[str]}`；写入 JSONB。 |
| `years_of_experience` | `int \| null` | 未明确时为 `null`；出现时必须为非负整数。 |
| `education` | `str \| null` | 未明确时为 `null`；最长 64。 |
| `expected_location` | `str \| null` | 未明确时为 `null`；最长 128。 |
| `expected_salary` | `str \| null` | 未明确时为 `null`；最长 64。 |

`target_job_titles` 是唯一必须从简历中取得的业务事实，且只取自简历显式“求职意向/目标岗位”栏目。MVP 假设每份上传的正式简历都包含该栏目；不实现缺失意向的兼容策略，也不得以最近任职岗位、技能或经历推断、推荐、补全或改写目标职位。其缺失、空白、超长或模型输出不符合任一 Schema 约束时，不得写入半成品画像，终态为 `schema_validation_failed`。其余字段未知时使用 `null` 或空数组，不得猜测填充。

## 5. 失败映射

| 故障情形 | 是否重试 | 终态 `failure_code` |
| --- | --- | --- |
| 关联对象非 `ready`、对象缺失或受控读取失败 | 是 | `storage_unavailable` |
| MinerU 调用超时 | 是 | `parser_timeout` |
| MinerU 网络异常、429 或 5xx | 是 | `internal_error` |
| PDF 损坏、加密后无法读取、扫描 PDF 或无有效机器文本 | 否 | `file_unreadable` |
| Markdown 输出为空、画像 JSON 无法校验或缺少目标职位 | 否 | `schema_validation_failed` |

可重试故障的次数、退避与超时完全沿用异步任务 MVP 基线。MinerU 与模型原始响应、文件正文、临时路径和原始异常不写入资源表、API 响应或任务失败分类。

## 6. 固定规则与验收

MVP 的解析任务 `task_version` 固定为内部常量 `v1`，仅维持既有幂等键约束；不提供规则升级、多版本并存、版本选择、版本比较或历史简历自动重解析。

首次交付须提供受控脱敏测试样本并验证：

1. 正常、可提取文本的 PDF 能生成通过校验的画像；
2. 扫描 PDF 或没有有效机器文本的 PDF 终态为 `file_unreadable`；
3. 可提取文本但没有目标职位的 PDF 终态为 `schema_validation_failed`；
4. MinerU 超时、429、5xx 与对象读取失败遵循既定重试和失败映射；
5. Worker 重投递或重复消息不会重复创建画像。
