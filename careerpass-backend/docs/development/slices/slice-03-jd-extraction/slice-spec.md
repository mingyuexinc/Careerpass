# Slice：S-03 岗位 JD 信息抽取

> 当前阶段：Close
>
> 当前状态：S03 核心 JD 解析实现、Capability Acceptance 和开发者最小演示验证已完成，`IS-S03-01` 已标记为 `integration_delivered`；其它测试层按各自边界维护专项证据。

## 1. 目标

将 S-02 已建立的岗位 JD 输入解析为经过校验的结构化岗位快照，供后续岗位查询和 S-08 岗位匹配使用。

S-03 的主要业务交付结果是成功快照中的 `fields`。`raw_sections` 只承担原文保真和追溯职责，不是 S-08 的主要匹配输入。

## 2. 输入

- S-02 已建立且归属于当前 HR 的 Job 和可读取 JD 文件；
- 受控内部验证场景中的 JD 本地存储路径；该路径必须指向受控存储根目录内、已登记为岗位输入的真实 Markdown 文件；
- 解析任务或内部验证请求提供的任务上下文。

## 3. 输出

成功时：

- 形成一个可供查询的岗位 JD 结构化快照；
- 快照包含五项有效核心字段，并允许包含额外字段；
- 结果可被 S-08 作为 `matching_ready` 岗位输入消费。

失败时：

- 存储暂不可用和临时技术失败有限次自动重试，耗尽后进入失败终态并允许手动重试；
- 可读内容非法直接失败并允许手动处理；
- 核心字段缺失直接失败并标记不可匹配，不形成快照；
- HR 可通过 `POST /api/v1/jobs/{job_id}/parse/retry` 对归属且尚未开始匹配的失败岗位生成下一代任务。

## 4. 前置条件

- S-02 已完成 Job、JD 文件和解析任务交接；
- JD 文件是当前演示范围内的 Markdown 文本文件；
- Job 归属和文件读取权限可以由服务端复核；
- 后端异步任务基础设施和 PostgreSQL 可用。

`Capability Acceptance` 只需要项目测试运行环境和固定 JD 文本，不需要上述 Job、任务和基础设施前置条件；上述资源归属、文件 `ready` 状态、任务约束和幂等规则由 `Slice Integration Test` 通过受控 Fixture、Factory 或 Setup 单独验证，不重复执行登录和 S-02 上传流程。

## 5. 业务规则

- 依赖 `BF-FLOW-008`、`BF-RULE-014`、`BF-STATE-010`、`BF-STATE-011`、`BF-SCOPE-010`、`BF-SCOPE-012` 和 `BF-SCOPE-014`；
- 成功快照必须具备岗位名称、工作地点、薪资、岗位职责和任职要求五项核心字段；
- 额外字段可以保留，但不构成当前 S-08 的固定必需输入；
- S-08 只消费解析成功且具备匹配资格的快照；
- 失败 Job 未删除时再次上传相同 JD 复用原 Job 并重建解析任务；已删除 Job 不复用，必须创建新 Job；
- 当前演示不定义已有旧快照再次解析失败时的清除或保留语义。

## 6. 范围 / 非目标

### 当前范围

- 固定 Markdown 标题解析；
- 五项核心字段和额外固定标题的结构化保存；
- 原文分段保留和确定性字段归一化；
- 异步任务提交、查询、重试、幂等和失败终态；
- 纯内部验证 API 的任务提交与结果查询；
- 固定 Fixture、自动前置数据构造、自动断言和 Acceptance Artifact；
- 向 S-08 交付成功结构化快照。

### 非目标 / 延期

- 不实现大模型摘要、职位同义归一或其他模型生成的语义扩展；
- 不实现 S-08 的匹配算法、匹配分数、推荐理由和结果展示；
- 不把本地路径 API 暴露为前端公开上传接口；
- 不在最小 Integration Scenario 中演示失败场景；
- 不处理结构校验失败分支；
- 不定义旧快照在再次解析失败后的清除或回滚。

## 7. 技术约束

- 必须使用现有 PostgreSQL、Repository、Dispatcher/Worker 和统一 `{code, msg, data}` 响应结构；
- 必须采用可追踪、幂等、可重试的异步任务；
- 任务持久化输入不得包含本地路径、文件正文、对象键或自由指令；
- 纯内部验证 API 的本地路径必须限制在配置的受控存储根目录内，并且不得进入响应、日志或追踪；
- 不调用大模型，解析结果必须经过 Schema 和业务规则校验后才能创建快照；
- Service 不得直接访问 ORM Session 或编写 SQL，所有数据访问经过 Repository。

## 8. 验收标准

- 开发者可以通过稳定的 Capability Acceptance 短命令输入固定 JD Fixture 并获得自动验收结果；不得要求开发者手工拼接请求或查询数据库；
- Capability Acceptance 只执行真实解析逻辑并输出核心 `fields`，不自动创建 Job、文件对象、任务或快照；
- 001、002 的成功 `fields` 符合参考 Schema，五项核心字段有效，职责和任职要求保留原文/条目；
- 额外固定标题不会导致成功解析结果丢失；
- Slice Integration Test 单独验证成功结果形成可供 S-08 消费的 `matching_ready` 快照；
- 自动断言按测试层分别覆盖核心字段、直接持久化、任务/基础设施和 Handoff 条件，并生成对应的 `report.md` 与 `actual.json`；
- 后端自测覆盖存储/技术异常有限次自动重试、非法内容和核心字段缺失手动失败且无快照、幂等和手动重建任务规则；
- 资源归属、内部路径、敏感内容和统一响应边界符合项目规则；
- 关联 Integration Scenario 的最小演示成功路径通过真实调用。

### 8.1 交付场景

| 项目 | 内容 |
| --- | --- |
| Integration Scenario | [`IS-S03-01`](../../../../../docs/integration/slices/slice-03-jd-extraction/integration-scenario.md) |
| Integration Contract | [`IC-S03-JD-EXTRACTION@0.2`](../../../../../docs/integration/slices/slice-03-jd-extraction/integration-contract.md) |
| 场景类型 | `internal_capability` |
| 交付目标测试代码文件夹 | [`tests/acceptance/s03_jd_parse/harness/`](../../../tests/acceptance/s03_jd_parse/harness/) 与 [`unit/`](../../../tests/acceptance/s03_jd_parse/unit/) |
| 交付目标测试结果目录 | `careerpass-backend/tests/acceptance/s03_jd_parse/delivery-acceptance-results/<run-id>/`；开发者重点审阅每次运行的 `report.md` 和 `actual.json` |
| 通用岗位 JD 数据目录 | [`tests/fixtures/job_descriptions/`](../../../tests/fixtures/job_descriptions/)；固定使用 001、002，不得移动 |
| 开发者核心能力自测入口 | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-jd-parse-capability.ps1`；输入 001、002，直接观察解析输出 |
| Slice/Infrastructure 专项入口 | 由对应 Slice Integration Test、Infrastructure Test 提供；不并入核心能力自测 |
| 验收产物 | `report.md`、`actual.json` 及命令输出的脱敏结果 |
| 开发者演示目标 | 运行固定核心能力命令，观察 001、002 的真实 `fields` 和人工可审阅产物 |
| 场景关闭条件 | Capability Acceptance 自动断言通过、产物已生成并由开发者审阅；其它测试层单独关闭 |

## 9. 开发者需裁决事项

无。当前剩余内容属于 Technical Design 和实现阶段的技术选择，不得改变本规格已确认的业务语义、范围和交付边界。
