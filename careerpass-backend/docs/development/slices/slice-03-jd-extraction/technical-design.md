# 切片：S-03 岗位 JD 信息抽取技术设计

> 本文档只记录 S-03 的技术落地方案和门禁证据。
>
> 业务目标、输入、输出、范围和验收标准以同目录的 [`slice-spec.md`](slice-spec.md) 为准；跨端语义以 [`IC-S03-JD-EXTRACTION`](../../../../../docs/integration/slices/slice-03-jd-extraction/integration-contract.md) 和 [`IS-S03-01`](../../../../../docs/integration/slices/slice-03-jd-extraction/integration-scenario.md) 为准。

## 1. 文档职责与事实源

### 1.1 本 Slice 技术事实

- Slice 规格：[`slice-spec.md`](slice-spec.md)；
- 跨前后端业务事实：[`business-baseline.md`](../../../../../docs/business/business-baseline.md)；
- API、异步任务和 Handoff Contract：本文档；
- Integration Contract 与 Integration Scenario：[`integration-contract.md`](../../../../../docs/integration/slices/slice-03-jd-extraction/integration-contract.md)、[`integration-scenario.md`](../../../../../docs/integration/slices/slice-03-jd-extraction/integration-scenario.md)；
- 领域模型：[`domain-model.md`](../../../domain/domain-model.md)；
- 数据库设计：[`database-design.md`](../../../data/database-design.md)；
- 异步任务架构：[`async-task-architecture.md`](../../../architecture/async-task-architecture.md)；
- 分层和安全规则：[`backend-guidelines.md`](../../backend-guidelines.md) 与后端入口规则。
- Slice Acceptance Test 规范：[`slice-acceptance-testing.md`](../../../../../docs/integration/slice-acceptance-testing.md)。

### 1.2 交付关联

| 项目 | 约定 |
| --- | --- |
| Integration Scenario | [`IS-S03-01`](../../../../../docs/integration/slices/slice-03-jd-extraction/integration-scenario.md) |
| Integration Contract | [`IC-S03-JD-EXTRACTION@0.2`](../../../../../docs/integration/slices/slice-03-jd-extraction/integration-contract.md) |
| 后端状态 | `backend_ready`；真实 Compose 拓扑、迁移和 S-03 任务链已验证 |
| 跨端交付状态 | `integration_delivered`；Capability Acceptance 短命令和开发者产物审阅已完成 |
| 场景类型 | `internal_capability`；稳定内部入口、任务结果和 Acceptance Artifact |
| 最小演示 | 在仓库根目录执行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-jd-parse-capability.ps1`，以固定 JD 文本核对真实解析 `fields` 并审阅 `report.md`、`actual.json` |

## 2. API、异步任务与交接契约

### 2.1 内部验证 API

#### `POST /internal/v1/s03/job-description/parses`

- 调用方：开发者验证程序；纯内部接口，不供正式前端或普通用户调用；
- 输入：`local_path`，必须是配置的受控 JD 存储根目录内的 Markdown 文件路径；
- 处理：验证路径、解析文件对象和 Job 归属，创建或复用本次解析任务；
- 成功结果：返回 `task_id` 和 `queued` 或 `running` 状态，不同步返回 `fields`；
- 失败结果：路径不在受控根目录、文件不可读或无法解析到有效 Job 时，返回统一受控错误，不泄露实际路径；
- 幂等：同一未删除 Job 存在 `queued/running` 任务时返回已有任务；已终态失败任务重新提交时按重建任务规则创建新任务；
- 安全：`local_path` 只在请求处理阶段使用，不进入任务持久化、响应、日志或追踪。

开发环境的受控 JD 根目录使用 `S03_JD_ROOT` 配置；未显式配置时，S-03 验收使用通用岗位 JD 数据目录 [`tests/fixtures/job_descriptions/`](../../../tests/fixtures/job_descriptions/)，其中的 001、002 脱敏构造 JD 用于真实演示和 S-03 验收输入，不得移动到 Slice 测试代码目录。

S-03 交付目标测试目录 [`tests/acceptance/s03_jd_parse/`](../../../tests/acceptance/s03_jd_parse/) 的语义明确为：测试代码和测试定义放在 `harness/`、`unit/` 等代码目录；Capability Acceptance 每次运行生成的 `<run-id>/report.md` 和 `actual.json` 放在 `tests/acceptance/s03_jd_parse/delivery-acceptance-results/`，是开发者重点关注的交付结果目录。001、002 JD 仍只从 `tests/fixtures/job_descriptions/` 读取；Capability Acceptance 不预置 Job、任务、快照或 `fields`。

#### `GET /internal/v1/s03/job-description/parses/{task_id}`

- 调用方：开发者验证程序；纯内部接口；
- 读取：只通过 Repository 查询任务和关联 Job，不接收路径；
- `queued/running`：返回任务状态，不返回 `fields`；
- `succeeded`：返回 `snapshot_id`、`parse_status=succeeded`、`matching_status=matching_ready`、`schema_version` 和成功快照的 `fields`；
- `failed`：返回脱敏的 `failure_semantics`、`failure_reason` 和必要的 `missing_core_fields`，不返回可供 S-08 使用的 `fields`；
- 响应：统一使用 `{code, msg, data}`，不返回内部路径、对象键、文件正文或原始异常。

正式前端不调用上述接口；S-02 的生产交接通过 Job 和 queued `AsyncTaskRun` 进入同一 S-03 用例。内部验证 API 只负责将受控本地路径解析为已登记的 Job/文件上下文后复用同一任务流程。

该 API 是稳定、受控的内部验证入口，不是临时旁路测试 API。它属于 S03 的 Slice Integration Test 入口，不是 Capability Acceptance 的核心能力入口。Capability Acceptance 直接调用核心解析能力；Slice Integration Test 再由专用 Harness 构造和清理 Job、文件对象及任务前置数据，管理动态 ID，执行断言并生成对应产物；开发者不手工调用 POST/GET 或查询数据库。

### 2.2 异步任务契约

| 项目 | 约定 |
| --- | --- |
| 任务标识与版本 | `job_jd_parse` / `v1` |
| Producer | S-02 上传事务；或内部验证 API |
| Consumer | Dispatcher → Celery Worker → S-03 Service |
| 持久化输入 | `job_id`、`stored_file_object_id`、任务版本和生成代数；不含路径、正文、对象键或自由指令 |
| 状态 | `queued → running → succeeded / failed` |
| 幂等 | 同一 Job 只能有一个活动任务；活动任务重复提交返回已有任务 |
| 重建 | 失败 Job 未删除时递增任务代数并创建新任务；已删除 Job 不复用，重新上传形成新 Job 和新任务 |
| 重试 | 临时技术失败自动重试，最多 3 次；采用有限退避，耗尽后 `failed` 且 `failure_reason=retry_exhausted` |
| 不重试 | 输入不可用和核心字段缺失立即 `failed` |
| 失败持久化 | 保存脱敏 `failure_semantics`、`failure_reason` 和必要的缺失核心字段；不得使用 `schema_validation_failed` 表达核心字段缺失 |

临时技术失败表示单次执行尝试失败，不是立即终态；任务只有重试耗尽后才进入失败终态。

### 2.3 Handoff Contract

| 项目 | 约定 |
| --- | --- |
| Producer | S-03 |
| Consumer | S-08 岗位匹配 |
| 触发条件 | 解析任务成功，五项核心字段有效，快照和任务状态在同一事务内提交 |
| 输入 | `job_id`、成功 `snapshot_id`、`schema_version`、`fields`、`matching_ready` |
| 输出 | 可查询的 `ParsedJobDescriptionSnapshot`；S-08 只消费成功 `fields` |
| 身份与归属 | `Job → HrProfile`，服务端复核 HR 归属；S-08 复核岗位可用性和匹配运行上下文 |
| 状态与幂等 | 失败不交接；成功快照只交给具备 `matching_ready` 的匹配运行；同一任务终态不可被迟到令牌覆盖 |
| 版本 | `Handoff-S03-JD@0.1` |

S-08 的额外消费字段集合仍由 S-08 Slice Design 决定；S-03 只保证五项核心字段和当前 `fields` 扩展结构稳定。

## 3. 领域实体与数据影响

### 3.1 实体使用

| 实体 | 本 Slice 用途 | 读写变化 | 归属/授权 | 全局事实源 | 处理结果 |
| --- | --- | --- | --- | --- | --- |
| Job | 解析资源和 S-08 交接锚点 | 查询 | `CurrentIdentity → HrProfile → Job`；任务上下文复核 Job | [`domain-model.md`](../../../domain/domain-model.md) | 已同步 |
| StoredFileObject | 读取已就绪 JD 文件元数据 | 查询 | 通过 Job 归属访问 | [`domain-model.md`](../../../domain/domain-model.md) | 已同步 |
| AsyncTaskRun | 保存解析任务状态、代数、幂等和失败语义 | 创建/更新 | 任务必须绑定 Job | [`domain-model.md`](../../../domain/domain-model.md) | 已同步 |
| ParsedJobDescriptionSnapshot | 保存成功结构化 JD 快照 | 成功时创建；失败不创建 | 通过 Job 归属读取 | [`domain-model.md`](../../../domain/domain-model.md) | 已同步 |

### 3.2 数据库影响

- 新增 `parsed_job_description_snapshots` 表：`id`、`job_id`、`schema_version`、`fields`、`raw_sections`、`created_at`；`job_id` 唯一，`fields` 和 `raw_sections` 使用 JSONB；
- 复用 S-02 已建立的 `job_jd_parse` / `job` 任务类型和资源类型；为 `async_task_runs` 保存可脱敏的 `failure_semantics`、`failure_reason`、缺失核心字段和任务代数；
- 成功事务：任务终态、快照、`matching_ready` 一起提交；
- 失败事务：任务终态和失败语义一起提交，不创建快照；
- 任务重建：旧失败任务保留历史，新任务使用新的代数和幂等键；
- Alembic：新增 S-03 revision，不修改已执行 revision；
- 全局数据设计需同步 S-03 快照表、任务类型和失败语义字段。

### 3.3 状态与业务规则同步

- `queued → running → succeeded / failed` 由 AsyncTaskRun 所有；
- 成功只允许 `matching_ready`，核心字段缺失为 `failed + matching_not_ready`；
- 临时技术失败可继续留在任务执行/重试过程，重试耗尽后进入 `failed`；
- 输入不可用和核心字段缺失不得重试；
- 业务规则引用 [`business-rules.md`](../../../product/business-rules.md)，不在代码中绕过状态迁移。

## 4. 技术实现方案

### 4.1 分层与调用链

```text
内部验证 POST / S-02 queued task
  → Controller / Task Consumer 校验输入和身份上下文
  → S03 Parse Service 编排文件读取、Markdown 解析和业务完整性校验
  → Repository 读取 Job、文件对象、任务并提交状态
  → Deterministic Markdown Parser 生成 fields/raw_sections
  → Pydantic/Schema 校验
  → Repository 原子提交成功快照或受控失败
  → GET 查询任务状态和成功 fields
```

### 4.2 实现边界

- API 层：只负责内部验证请求、任务查询、统一响应和安全输入校验；
- Service 层：编排 Job/文件复核、解析、核心字段完整性判定、重试分类和快照提交；
- Repository 层：负责 Job、StoredFileObject、AsyncTaskRun 和快照的查询、归属校验、状态迁移和事务；
- Parser：只按固定 Markdown 标题和确定性规则提取原文、条目、来源顺序和可选归一化值；
- Infrastructure：复用对象存储/本地受控文件读取、Dispatcher、Celery Worker 和 PostgreSQL；
- S-08：只接收成功且 `matching_ready` 的快照，不读取原文并重新解析。

### 4.3 分层测试

- `Capability Acceptance` 使用 001、002 固定 JD 文件，直接调用真实核心解析逻辑，验证核心字段、额外字段、原文保真和固定 Expected / Actual；开发者从仓库根目录执行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-jd-parse-capability.ps1`；不构造 Job、任务、快照，不连接 PostgreSQL、Redis、Celery 或完整 API 链路；
- `Slice Integration Test` 单独验证正式内部入口、Job/StoredFileObject 前置条件、Repository、事务、成功快照和当前 Slice 的直接持久化；
- `Infrastructure Test` 单独验证 Redis、Dispatcher、Celery Worker、租约、重试和消息消费；
- `Cross-Slice Integration Test` 单独验证 S-02→S-03 的输入交接和 S-03→S-08 的成功快照交接；
- `E2E Test` 单独验证登录、上传、解析到匹配的完整用户流程；
- 各层均可生成自己的脱敏 `report.md`、`actual.json`；Capability Acceptance 的产物只展示核心能力实际输出，不把其它层结果混入。

### 4.4 局部实现决策

| 决策 | 选择 | 简短理由 |
| --- | --- | --- |
| 解析方式 | 确定性 Markdown 标题解析 | 当前版本不实现大模型语义解析，保证结果可重复 |
| 成功快照 | `job_id` 唯一的当前有效快照 | 当前版本不建立 JD 版本链，旧快照失败回滚不在范围内 |
| 任务代数 | 同一 Job 的失败重建任务递增代数 | 保留失败历史并避免旧任务覆盖新任务 |
| 失败语义 | `temporary_technical_failure`、`input_unavailable`、`core_fields_missing` | 与业务基线一致，不引入结构校验失败分支 |
| 核心字段缺失 | 失败且不创建快照 | 成功 Schema 只描述可供 S-08 使用的完整快照 |

## 5. 外部依赖、失败处理与安全边界

### 5.1 依赖与证据

| 依赖 | 用途 | 真实证据 | 状态 |
| --- | --- | --- | --- |
| PostgreSQL | Slice Integration Test 的 Job、文件对象、任务和快照持久化 | `20260815_0008` migration；迁移版本和约束真实查询通过 | 由 Slice Integration Test 负责 |
| Redis/Celery/Dispatcher/Worker | Infrastructure Test 的任务投递、执行、租约和有限重试 | Compose healthy；Worker 注册并成功消费 `careerpass.job_jd_parse` | 由 Infrastructure Test 负责 |
| 受控本地 JD 存储 | 内部验证 API 的输入文件 | Backend 受控目录挂载；真实 API 路径校验和 SHA-256 登记匹配通过 | 已确认 |
| Markdown Parser | 固定标题确定性解析 | `test_job_description_parser.py` | 通过 |
| LLM/外部语义服务 | 本 Slice 不使用 | 不适用 | 不适用 |

### 5.2 失败处理

- 输入路径不在受控根目录、文件对象不存在、文件不可读取或编码无法解码：`input_unavailable`，立即失败，不重试；
- 单次执行发生可重试的临时连接、Worker 或基础设施故障：记录本次尝试失败并自动重试；重试耗尽后 `failure_reason=retry_exhausted`；
- Dispatcher/Worker 处理 S-03 迟到租约或执行超时时，写入 `temporary_technical_failure + execution_timeout`，不写旧的 `failure_code`；
- 五项核心字段任一缺失：`core_fields_missing`，立即失败、`matching_not_ready`，不创建快照；
- S-02 上传阶段无法建立 ready 文件对象：属于 S-02 上传失败，不由 S-03 反向改写上传结果；
- 解析成功：在同一事务内写入快照和成功任务终态；
- 任务旧令牌或迟到回调：拒绝状态覆盖，不创建重复快照；
- 失败 Job 未删除再次提交：复用 Job、创建新任务代数；已删除 Job：由 S-02 新建 Job 后创建新任务；
- 当前不处理已有旧快照再次解析失败的清除或保留语义。

### 5.3 敏感信息

- 不得进入响应、日志或追踪：本地路径、对象键、文件正文、原始异常、凭证和模型原始响应；
- 脱敏诊断字段：`request_id`、`task_id`、`job_id`、阶段、状态、失败语义、失败原因、耗时、重试次数；
- Prompt、任务输入和外部请求：本 Slice 不使用 LLM，不产生外部模型请求；任务只接收已校验资源标识。

## 6. 实现决策记录

### 6.1 开发者需裁决事项

无。业务范围、失败语义、重试原则、重传规则、内部验证 API 边界和最小演示范围均已裁定。

### 6.2 设计变化与回退

| 发现的变化 | 影响 | 回退 Gate | 处理结果 |
| --- | --- | --- | --- |
| 无 | 无 | 不适用 | 设计已收口，Implement、Verify 和 Close 已完成；真实 `IS-S03-01` 已交付 |

## 7. Readiness Check、验证结果与关闭结论

### 7.1 Readiness Check

| 检查项 | 通过标准 | 当前结果 |
| --- | --- | --- |
| 业务事实 | S-03 相关业务基线均为 `confirmed` | 通过 |
| Slice Scope | `slice-spec.md` 与 Integration Scenario 目标一致 | 通过 |
| Integration Contract | Contract 锁定 API 模式、状态、失败和交接语义 | 通过 |
| 数据设计 | 快照表、任务代数、失败语义和事务边界已同步 | 通过，`20260815_0007`、`20260815_0008` |
| API 安全 | 内部路径受控，公开前端不调用 | 通过，S-03 API 单元测试 |
| 异步基础设施 | Dispatcher、Worker、租约和重试可运行 | 通过；PostgreSQL/Redis healthy，Dispatcher 投递，Worker 注册并成功消费 `careerpass.job_jd_parse` |
| 真实 JD 输入 | 受控根目录有脱敏 Markdown 演示文件 | 通过；S-02 上传建立 Job/StoredFileObject，S-03 API 查询成功快照 |
| 外部模型 | 本 Slice 不依赖 LLM | 通过 |

| 启动门禁证据 | 记录 |
| --- | --- |
| 故障案例匹配 | `Docker CLI 文件存在但当前执行上下文拒绝运行`、`误判 Docker 未安装：CLI 已安装但当前 Shell 无法执行` |
| 统一预检命令 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend-readiness.ps1` |
| 执行上下文 | 默认上下文返回 `execution_denied`；随后按门禁在授权上下文重跑 |
| 预检状态与时间 | `status=ready`；Docker CLI、Engine、Compose、`desktop-linux` context 和 Compose 配置通过；2026-08-15 09:01 +08:00 |

统一预检已证明 Docker/Compose 可用，纠正“当前环境无法运行 Docker CLI”的旧假设；该证据不替代 PostgreSQL、Redis、Dispatcher、Worker 和真实 API 链路验证。

Readiness Check 已具备真实 PostgreSQL、Redis、Worker、Dispatcher 和内部 API 运行证据，后端状态为 `backend_ready`。Capability Acceptance 短命令已执行通过，开发者已审阅 Acceptance Artifact，因此 `IS-S03-01` 已标记为 `integration_delivered`。

### 7.2 验证证据

| 验证类型 | 覆盖内容 | 结果 | 证据 |
| --- | --- | --- | --- |
| Schema | 成功 `fields` 五项核心字段和扩展字段 | 通过 | Pydantic Schema、Parser 单元测试 |
| Service/Parser | 固定标题、原文、额外字段和核心字段完整性 | 通过 | S-03 单元测试 |
| Capability Acceptance | 001、002 核心解析输出和 Expected / Actual | 通过；开发者已审阅两份实际解析结果 | `IS-S03-01` 第 4 节；`20260815T071301Z-ad3d5f27` |
| Slice Integration | 内部入口、Job/文件对象、快照和数据库事务 | 由专项集成测试记录 | S03 Slice Integration Test |
| Infrastructure | Redis、Dispatcher、Worker、重试和任务消费 | 由基础设施专项测试记录 | Infrastructure Test |
| Cross-Slice | S-02→S-03、S-03→S-08 真实交接 | 由跨 Slice 测试记录 | Cross-Slice Integration Test |
| E2E | 登录、上传、解析到匹配 | 由少量主流程测试记录 | E2E Test |

### 7.3 关闭结论

- `slice-spec.md` 与最终实现一致：是；
- 本文档与代码、迁移和测试一致：是；
- 全局领域、数据和业务事实已同步：是；
- Handoff Contract 可供下游使用：是；成功快照已具备 `matching_ready`；
- Integration Contract 与真实 API 一致：是；真实提交、查询和响应字段已核对；
- Integration Scenario 第 4 节 Capability Acceptance：已执行命令并审阅产物；
- 未决开发者裁决：无；
- 最终结论：`integration_delivered`；S03 核心 JD 解析开发交付目标已完成，其它测试层按各自范围继续维护专项证据。
