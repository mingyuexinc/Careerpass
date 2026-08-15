# Integration Scenario：<场景名称>

> 本文档定义一个可演示、可整改和可关闭的最小跨端交付单元。
>
> Integration Scenario 不是全面自测记录，只记录能够初步证明当前环节交付成功的最小必要演示信息。全面的边界、异常、权限、幂等和数据一致性测试由对应测试或专项自测文档负责。

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `<例如 IS-S02-01>` |
| 名称 | `<内容>` |
| 关联 Slice | `<一个或多个 Slice>` |
| Integration Contract | `<路径和版本>` |
| 场景类型 | `frontend_visible` / `internal_capability` |
| 内部能力测试层 | `Capability Acceptance` / `Slice Integration` / `Infrastructure` / `Cross-Slice` / `E2E` |
| 交付状态 | `draft` / `contract_locked` / `backend_ready` / `integration_blocked` / `integration_delivered` |

## 2. 交付目标

从开发者可执行的最小交付路径描述目标。`frontend_visible` 场景填写用户路径；`internal_capability` 场景必须先声明测试层。开发者最小自测通常填写 `Capability Acceptance` 的核心业务输入、核心处理和实际输出；直接持久化、公共基础设施、跨 Slice 交接和完整用户流程分别引用对应专项测试，不得全部塞入核心能力自测：

```text
<角色登录 → 页面操作 → 系统处理 → 用户可观察结果>
<核心业务输入 → 核心能力处理 → 核心业务输出 → Acceptance Artifact>
```

只写本场景和所声明测试层必须交付的最小行为，不把上游已验证步骤、共享基础设施、全面异常验证、未完成的下游能力或视觉占位数据写成核心能力成功条件。

## 3. 前置条件与演示数据

- 环境：`<前端、后端、数据库、队列等>`
- 已建立的身份和前置状态：`<例如已登录的角色和已完成的上游场景>`
- 演示数据：`<文件、输入、初始状态>`
- 数据准备方式：`<固定 Fixture / 受控上传 / 初始化脚本>`
- 交付目标测试代码文件夹：`<tests/ 下同一交付目标目录；包含 Test、Factory、Repository、Unit Test 和 Expected Manifest>`
- 交付目标测试结果目录：`<上述目录下明确命名的结果目录；开发者重点审阅 report.md 和 actual.json>`
- 通用真实演示数据目录：`<例如 tests/fixtures/job_descriptions/；不得移动到交付目标测试代码目录>`
- 依赖场景：`<已通过的场景>`
- 自动验收命令：`<稳定短命令>`
- Acceptance Artifact：`<report.md 和 actual.json 输出目录>`

## 4. 演示步骤与预期结果

> 本节按测试条目填写，不按每个操作动作拆分记录。同一测试条目包含多个连续操作步骤时，应在“操作”字段中完整描述这些步骤，并合并为表格中的一条记录。

| 步骤 | 操作 | 预期系统结果 | 预期页面结果或验收产物 |
| --- | --- | --- | --- |
| 1 | `<最小必要操作>` | `<结果>` | `<页面结果；内部能力场景填写 Artifact>` |

## 5. 最小演示验证结果

> 本节只能由开发者在实际完成最小演示后填写。Coding Agent 不得代为生成、补写或推断验证结果和证据，也不得将代码检查、自动化测试或后端核对结果代替开发者演示记录。

> 对 `internal_capability` 场景，本节默认记录开发者的 Capability Acceptance 自测：输入一个或多个固定业务样本，观察核心能力实际输出。数据库、Redis/Celery、跨 Slice 和 E2E 结果不写入本节，改由对应专项测试记录。

| 步骤 | 操作 | 实际结果 | 其它问题 |
| ---- | ---- | -------- | -------- |
| `<步骤>` | `<操作>` | `<待开发者填写>` | `<待开发者填写>` |

## 6. 问题与整改

> 本节由 Coding Agent 根据“最小演示验证结果”中的“其它问题”逐一填写。每一项“其它问题”对应本节一条记录，问题数量必须保持一致；Coding Agent 只能填写最右侧“验收结果”之前的列，不得新增未在“其它问题”中发现的问题，也不得代为填写第 5 节或“验收结果”。

| 记录编号 | 问题类型 | 原因与分析 | 整改结果 | 验收结果 |
| -------- | -------- | ---------- | -------- | -------- |
| `<开发者发现问题后填写>` | `<开发者填写>` | `<开发者填写>` | `<待整改/已完成>` | `<仅开发者填写>` |

问题分类至少区分：`contract_mismatch`、`frontend_mapping_error`、`backend_implementation_error`、`business_scope_error`、`environment_error`、`test_data_error`。

## 7. 关闭结论

- 最小演示步骤通过：`是 / 否`
- 问题已整改并完成回归：`是 / 否 / 不适用`
- 问题验收结果：`仅由开发者填写`
- 前端 Mock、真实 API 和页面结果或 Acceptance Artifact 一致：`是 / 否 / 不适用`
- Acceptance Artifact 已生成并由开发者审阅：`是 / 否 / 不适用`
- 最终结论：`Integration Delivered / integration_blocked`
