# Integration Scenario：IS-S03-01 岗位 JD 解析

> 本场景属于 `internal_capability`。它允许以稳定内部入口、任务结果和 Acceptance Artifact 作为交付目标；不验证前端岗位上传页，也不以预构造 `fields` 代替真实解析。

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `IS-S03-01` |
| 名称 | 开发者运行 JD 解析 Capability Acceptance 并核对核心输出 |
| 关联 Slice | `S-03` |
| Integration Contract | [`integration-contract.md`](integration-contract.md) `IC-S03-JD-EXTRACTION@0.2` |
| 场景类型 | `internal_capability` |
| 执行目录 | 仓库根目录 `Careerpass/` |
| 内部能力测试层 | `Capability Acceptance`；只验证 JD 解析核心能力 |
| 开发者核心能力自测命令 | 在仓库根目录执行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-jd-parse-capability.ps1` |
| Capability Acceptance Artifact | `careerpass-backend/tests/acceptance/s03_jd_parse/delivery-acceptance-results/<run-id>/report.md` 与 `actual.json` |
| 交付目标测试代码文件夹 | `careerpass-backend/tests/acceptance/s03_jd_parse/harness/` 与 `unit/` |
| 交付目标测试结果目录 | `careerpass-backend/tests/acceptance/s03_jd_parse/delivery-acceptance-results/`；开发者重点审阅每次运行的 `report.md` 和 `actual.json` |
| 通用岗位 JD 数据目录 | `careerpass-backend/tests/fixtures/job_descriptions/`；固定使用 001、002，不得移动 |
| 交付状态 | `integration_delivered` |

## 1. 交付目标

本场景的开发者自测目标是 S-03 的核心 JD 解析能力：以固定 JD 文本为输入，执行真实解析逻辑，输出结构化 `fields` 和可人工审阅的结果。Capability Acceptance 不执行登录、S-02 上传、Job/StoredFileObject 前置构造、数据库查询、Redis/Celery、Dispatcher/Worker、S-08 匹配或完整用户流程。

测试代码使用 [`tests/acceptance/s03_jd_parse/harness/`](../../../../careerpass-backend/tests/acceptance/s03_jd_parse/harness/)；固定输入只从 [`tests/fixtures/job_descriptions/`](../../../../careerpass-backend/tests/fixtures/job_descriptions/) 下的 001、002 读取，不移动或复制 JD 数据。Capability Acceptance 结果统一生成到 `careerpass-backend/tests/acceptance/s03_jd_parse/delivery-acceptance-results/<run-id>/`，开发者重点审阅其中的 `report.md` 和 `actual.json`。不得预置 `fields`、快照或成功状态。

```text
运行固定 JD 解析 Capability Acceptance 短命令
→ 读取 001、002 固定 JD 文本
→ 执行真实 S-03 核心解析逻辑
→ 自动断言核心字段、额外字段和原文保真
→ 生成并审阅 report.md、actual.json
```

数据库持久化和正式内部入口属于 `Slice Integration Test`；Redis、Celery、Dispatcher、Worker 属于 `Infrastructure Test`；S-03 与 S-08 的交接属于 `Cross-Slice Integration Test`；登录、上传到匹配属于 `E2E Test`。这些结果可以作为 S03 交付证据，但不纳入本节的核心能力自测。

## 2. 前置条件与演示数据

- 环境：S-03 核心解析运行环境和项目 Python 测试依赖可用；
- 身份：Capability Acceptance 不需要登录身份；登录接口和 S-02 上传不列入本场景步骤；
- 输入：固定使用 `tests/fixtures/job_descriptions/` 下的 001、002 两份脱敏构造 Markdown JD；
- 数据准备：由 Capability Acceptance 直接读取固定 Fixture，不构造 Job、文件对象、任务或快照；
- 参考：[`fields.schema.json`](fields.schema.json) 和预期字段核对表；
- 范围：本节只验证“JD 文本 → 解析结果”；其它工程链路由对应专项测试负责。

## 3. 演示数据要求

演示 JD 至少包含：

- 当前匹配所需的岗位名称、工作地点、薪资、岗位职责和任职要求；
- 一个额外固定标题，例如公司名称、岗位性质、用工类型或面试方式；
- 至少一段较长职责文本或多条职责列表，用于确认 S-03 保存职责原文/条目；
- 主路径演示数据保证五项核心字段均有效；最小演示只验收成功解析结果；
- 不得在输入中预先写入 `fields` JSON，也不得把前端 Mock 岗位对象作为解析结果。

## 4. 最小演示验证结果

本节是开发者的核心能力自测记录，不是 S03 全链路交付报告。执行位置统一为仓库根目录 `Careerpass/`，完整命令为：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-jd-parse-capability.ps1
```

该命令读取 001、002 两份固定 JD，直接执行 S-03 解析逻辑，生成 `careerpass-backend/tests/acceptance/s03_jd_parse/delivery-acceptance-results/<run-id>/report.md` 和 `actual.json`，并以自动断言结果作为进程退出码。

本节不得要求开发者启动或检查 PostgreSQL、Redis、Dispatcher、Worker，不得手工登录、上传、调用内部 API 或查询数据库。当前包含这些链路的 `test-jd-parse.ps1` 只能归类为 Slice/Infrastructure Integration 证据，不能作为本节的核心能力自测命令。

| 记录编号 | 操作                                                         | 实际结果                                                     | 其它问题 |
| -------- | ------------------------------------------------------------ | ------------------------------------------------------------ | -------- |
| 1        | 在仓库根目录执行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-jd-parse-capability.ps1`，读取固定的 001、002 JD 并运行真实解析 | 查看`20260815T071301Z-ad3d5f27`生成两份实际解析结果；岗位名称、公司、地点、薪资、职责、任职要求和额外标题与 Expected 对比通过； | 无       |

## 5. 问题与整改

> 本次开发者最小演示的“其它问题”为“无”，不新增问题整改记录。

| 记录编号 | 问题类型 | 原因与分析 | 整改结果 | 验收结果 |
| --- | --- | --- | --- | --- |
| — | 无 | 本次核心能力自测未发现其它问题 | 不适用 | 开发者已确认 |

## 6. 关闭结论

- S-03 Capability Acceptance 短命令：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-jd-parse-capability.ps1`；
- 本节自动断言：只覆盖 001、002 的真实 `fields`、核心字段、额外字段、原文保真和 Expected / Actual，执行结果为通过；
- 持久化、任务状态、Redis/Celery、S-08 Handoff 和完整用户流程：分别由对应专项测试记录，不作为本节开发者自测结果；
- Acceptance Artifact：已生成并由开发者审阅 `careerpass-backend/tests/acceptance/s03_jd_parse/delivery-acceptance-results/20260815T071301Z-ad3d5f27/`；
- 最终结论：`integration_delivered`，S03 核心 JD 解析开发交付目标已完成。
