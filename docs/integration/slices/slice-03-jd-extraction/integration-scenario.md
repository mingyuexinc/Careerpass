# Integration Scenario：IS-S03-01 开发者验证 JD 解析结果

> 本场景验证 S-03 通过纯内部验证 API，从真实 JD 输入生成结构化 `fields`；不验证前端岗位上传页，也不以预构造 `fields` 代替真实解析。

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `IS-S03-01` |
| 名称 | 开发者调用 JD 解析 API 并核对 `fields` |
| 关联 Slice | `S-03` |
| Integration Contract | [`integration-contract.md`](integration-contract.md) `IC-S03-JD-EXTRACTION@0.2` |
| 交付状态 | `draft` |

## 1. 交付目标

开发者准备一份真实或脱敏构造的 Markdown JD，将其放置在受控本地存储根目录内；开发环境可直接使用 [`s03_demo_ai_application_engineer.md`](../../../../careerpass-backend/tests/fixtures/job_descriptions/s03_demo_ai_application_engineer.md)。通过 S-03 纯内部验证 API 提交本地存储路径并查询任务结果，确认成功结果符合 [fields JSON Schema](fields.schema.json)，且字段内容来自实际文件，而不是预置 `fields` Mock。

```text
准备真实 `.md` JD 并取得受控本地存储路径
→ 调用 S-03 内部解析任务提交 API
→ 通过 task_id 查询解析结果
→ 查看 parse_status、matching_status 和 fields
→ 按 Schema、原文和预期字段核对结果
```

## 2. 前置条件与演示数据

- 环境：后端服务、数据库、受控对象存储和 S-03 解析运行环境可用；
- 身份：开发者使用受控 HR 身份，或使用 Technical Design 明确的内部验证身份；
- 输入：至少一份包含固定标题和额外固定标题的真实或脱敏构造 Markdown JD；
- 数据准备：准备受控本地存储根目录内的 JD 文件和本地存储路径；开发环境默认使用 [`careerpass-backend/tests/fixtures/job_descriptions/`](../../../../careerpass-backend/tests/fixtures/job_descriptions/)；
- 参考：[`fields.schema.json`](fields.schema.json) 和预期字段核对表；
- 依赖场景：`IS-S02-01` 或等价的可解析 Job 输入已建立。

## 3. 演示数据要求

演示 JD 至少包含：

- 当前匹配所需的岗位名称、工作地点、薪资、岗位职责和任职要求；
- 一个额外固定标题，例如公司名称、岗位性质、用工类型或面试方式；
- 至少一段较长职责文本或多条职责列表，用于确认 S-03 保存职责原文/条目；
- 主路径演示数据保证五项核心字段均有效；最小演示只验收成功解析结果；
- 不得在输入中预先写入 `fields` JSON，也不得把前端 Mock 岗位对象作为解析结果。

## 4. 演示步骤与预期结果

| 步骤 | 操作 | 预期系统结果 | 预期结果核对 |
| --- | --- | --- | --- |
| 1 | 准备真实 `.md` JD 并取得受控本地存储路径，调用 S-03 内部 JD 解析任务提交 API，再使用返回的 `task_id` 查询结果，观察 `parse_status`、`matching_status` 和 `fields`，并对照原始 JD、固定标题、额外标题和 S-08 交接要求核对结果 | 主路径成功时返回已校验的 `fields` 和 `matching_ready`，并形成可供 S-08 使用的成功快照 | `data.fields` 符合 [`fields.schema.json`](fields.schema.json)，字段来自真实 JD，职责保留原文/条目，未知标题不导致结果丢失，不出现大模型摘要或职位同义扩展字段，S-08 无需重新读取 Markdown |

## 5. 最小演示验证结果

> 本节只能由开发者在实际调用 API/验证程序后填写。Coding Agent 不得代为生成、补写或推断验证结果和证据。

| 步骤 | 操作 | 实际结果 | 其它问题 |
| --- | --- | --- | --- |
| `<步骤>` | `<开发者填写实际 API/验证操作>` | `<待开发者填写>` | `<待开发者填写>` |

## 6. 问题与整改

> 本节由 Coding Agent 根据“最小演示验证结果”中的“其它问题”逐一填写；未完成开发者演示前不得预填问题或验收结论。

| 记录编号 | 问题类型 | 原因与分析 | 整改结果 | 验收结果 |
| --- | --- | --- | --- | --- |
| `<开发者发现问题后填写>` | `<开发者填写>` | `<开发者填写>` | `<待整改/已完成>` | `<仅开发者填写>` |

## 7. 关闭结论

- API/验证程序真实调用完成：`是 / 否`；
- `fields` Schema 核对完成：`是 / 否`；
- 原文、固定标题和额外字段核对完成：`是 / 否`；
- S-08 交接核对完成：`是 / 否 / 不适用`；
- 最终结论：`Integration Delivered / integration_blocked`，仅由开发者根据实际证据填写。
