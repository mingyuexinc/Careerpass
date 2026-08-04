# 阶段 3：简历解析与候选人画像分支方案设计

> 阶段状态：`passed`（开发者已于 2026-08-02 完成人工方案门禁复核）。设计依据：`01-analysis/requirements.md`、`01-analysis/impact-analysis.md`、`02-validation/prevalidation.md`、`02-validation/worker-prevalidation.md`，以及项目接口协议、数据模型、异步任务技术方案、对象存储技术方案和简历解析技术方案。本文只固化本变更的实现边界，不替换统一契约注册表。

> 跨开发包基线：本模块是 `ResumeParseRequestV1@v1` 的 consumer；唯一契约文件为 `.harness/contracts/resume-parse-request-v1.yaml`，状态为 `locked`，联合门禁为 `JCG-2026-020-021-RESUME-PARSE-V1`，`contract_hash` 为 `9AB937AE08E4A69C3D1D87C1968B8C17D7B6371984E236B1481C984F49EC9B18`。CHG-020 是唯一 producer，G2 在资源事务中创建或复用 queued `AsyncTaskRun`，G3 只消费既有 queued 任务。

## 1. 设计目标与边界

### 1.1 目标

- 接收候选人资料准备模块提交的版本化 `ResumeParseRequestV1`，消费 G2 已创建或复用的 queued `resume_parse` 异步任务。
- 通过独立 Dispatcher、Redis Broker 和 Celery Worker 执行受控简历解析。
- 经 Repository 完成候选人归属、资源状态、对象可读性和执行租约校验。
- 按固定链路执行：受控对象读取 → MinerU MCP 文本提取 → Qwen Plus 结构化画像 → Pydantic/业务规则校验 → 原子终态写入。
- 成功时只产生一份完整 `CandidateProfile`；失败时只产生允许暴露的 `failure_code` 和明确失败终态。

### 1.2 不在本方案内

- 文件上传、自动脱敏、OCR、扫描 PDF、原始文件下载或预览；这些由候选人资料准备模块或明确延期范围负责。
- Agent 决定是否解析、传入路径/URL/MCP 参数/模型指令，或直接读取 ORM、SQL 和本地文件。
- 独立画像任务、画像重跑 API、历史版本、SSE/WebSocket/Webhook、通用任务运营后台和用户手动重跑。
- Redis Result Backend、通用高可用平台、批量解析和生产规模优化。

## 2. 模块与能力边界

| 模块/闭环 | 类型 | 拥有边界 | 上游契约 | 下游契约 | MVP 交付顺序与门禁 |
| --- | --- | --- | --- | --- | --- |
| 候选人资料准备 | 业务模块 | 上传、对象建档、简历归属和 `ResumeParseRequestV1` 契约交接；在同一事务中创建或复用 queued `AsyncTaskRun`；不调用 G3 Service/Dispatcher/Worker，不拥有画像和解析终态 | 已归属且对象 `ready` 的正式简历 | `ResumeParseRequestV1` | CHG-020 阶段 3 与联合契约门禁通过 |
| 简历解析与候选人画像 | 跨模块集成闭环 | 任务执行、受控读取、画像原子写入、简历/任务解析终态和查询 | `ResumeParseRequestV1@v1` | `CandidateProfile`、简历状态、脱敏失败分类 | 阶段 1–3 已通过；契约已锁定；阶段 4 尚未启动 |
| 岗位匹配 | 下游业务模块 | 只消费已校验画像契约，不读简历正文和内部对象 | `CandidateProfile` | 匹配输入快照 | 后续模块 |

| 技术能力 | 提供者 | 状态 | 首个真实消费者 | 输入/输出契约 | 运行时依赖与门禁 |
| --- | --- | --- | --- | --- | --- |
| 受控资源读取 | Repository + 对象存储适配器 | 复用且已预验证 | Resume Worker | `resume_id` → 内存 PDF 字节 | 对象 `ready`、候选人归属和受控读取授权 |
| 可靠异步执行 | Dispatcher + Redis + Celery Worker | 已完成真实预验证 | Resume Worker | `task_run_id` → 任务终态 | `async_task_runs`、执行租约、令牌和至少一次投递 |
| 文本提取 | MinerU MCP 适配器 | 复用真实预验证 | Resume Worker | 受控临时 PDF → 内存 Markdown | stdio Bridge、显式超时、禁用 OCR |
| 结构化画像 | Qwen Plus 适配器 + Pydantic | 复用真实预验证 | Resume Worker | Markdown → `ResumeProfileExtractionV1` | JSON Schema、业务规则和失败映射 |
| 终态写入 | DocumentParsingRepository | 已有实现/需本模块联调 | Resume Worker | 租约 + 校验画像 → 原子数据库结果 | 同事务锁定任务与简历，唯一画像约束 |

### 2.1 外部技术能力复用裁决

阶段 2 的技术结论为 `passed`。本方案不新增或替换外部技术能力，以下能力仅按既有证据复用：

| 能力 | 阶段 2 结论 | 本方案采用方式 | 本方案不宣称的内容 |
| --- | --- | --- | --- |
| PostgreSQL / Repository | `passed`（复用） | 以 PostgreSQL 作为任务、简历和画像终态的权威存储；所有读写经过 Repository | 不把阶段 2 证据当作本模块阶段 6/8 业务验收 |
| 受控对象存储 | `passed`（复用） | 按资源归属和对象 `ready` 状态受控读取；通过临时文件交给 MinerU | 不提供原始文件下载、预览或对象定位信息 |
| Redis Broker / Dispatcher | `passed`（复用 + 真实复验） | Dispatcher 扫描已提交 queued 任务并向 Redis 投递同一 `task_run_id` | 不由 G3 创建任务，不把 Broker 消息当作业务状态权威 |
| Celery Worker | `passed`（真实复验） | 领取数据库执行租约，处理重复投递、重试、超时和 Worker 丢失接管 | 不以阶段 2 复验替代本模块阶段 6/8 端到端验收 |
| MinerU MCP / Qwen Plus | `passed`（复用 + 真实复验） | 分别执行文本提取和严格结构化画像生成 | 不把供应商调用成功直接视为画像业务成功 |

阶段 2 没有新增供应商级首次验证能力。方案阶段只负责把已验证能力装配到 CHG-021 的责任边界中；G2→G3 真实业务交接、画像原子写入和完整终态验收留待后续阶段。

## 3. 总体架构与数据流

```text
候选人资料准备模块
    │  ResumeParseRequestV1 契约交接（仅 candidate_id、resume_id、task_version=v1；非 Service 调用）
    ▼
PostgreSQL: resumes + stored_file_objects + async_task_runs(queued)
    │
    ▼
Dispatcher ── publish ──> Redis Broker ──> careerpass.resume_parse
                                             │ task_run_id
                                             ▼
                                      Celery Worker
                                             │ claim_execution()
                                             ▼
                              Repository 校验 + execution_token
                                             │
                              受控对象读取（临时文件）
                                             ▼
                              MinerU MCP → 内存 Markdown
                                             ▼
                              Qwen Plus → Pydantic/业务校验
                                             ▼
DocumentParsingRepository 原子事务
  ├─ candidate_profiles（成功唯一写入）
  ├─ resumes.parse_status
  └─ async_task_runs.status / failure_code / lease cleanup
```

Dispatcher 只向 Broker 投递 `task_run_id`；Celery 消息不携带路径、URL、对象键、正文、模型参数或自由指令。Worker 通过 Repository 重新加载任务、简历、候选人和对象状态，重新校验 `ResumeParseRequestV1@v1` 的三个字段及归属后，才领取执行租约。权威状态只来自 PostgreSQL 的 `resumes` 与 `async_task_runs`；Celery Result Backend 不启用。前端通过 `GET /api/v1/resumes` 自动查询简历状态，成功后再查询画像，不要求用户手动刷新。

## 4. 触发、任务与接口设计

### 4.1 上游触发契约

`ResumeParseRequestV1` 由候选人资料准备模块在正式 PDF 已完成上传校验、对象建档、归属校验且对象为 `ready` 后，通过固定跨模块契约完成交接；G2 同一 PostgreSQL 事务创建或复用 `AsyncTaskRun(status=queued)`。该交接不调用文档解析 Service、Dispatcher 或 Worker；G3 从已有 queued 任务开始消费。请求只允许 `candidate_id`、`resume_id` 和 `task_version="v1"`，且 Schema 使用 `extra="forbid"`；不得携带受控读取授权、幂等键、真实路径、URL、对象键、文件正文、MCP 参数、模型参数或自由指令。解析模块以任务记录中的 `resume_id` 和固定版本为准，不能从客户端输入推导资源定位。

契约交接的责任边界如下：G2 负责证明资源已归属当前候选人且对象已 `ready`，并创建/复用唯一 queued `resume_parse` 任务；G3 负责消费已有任务、重新校验交接和资源状态，并执行解析。任何一侧均不得通过对方内部 Service、Worker 或模型适配器完成联调。

创建任务与简历进入 `processing` 的数据库写入必须幂等；同一资源、任务类型和 `task_version=v1` 只能保留一个有效任务运行。重复提交复用已有任务，不创建第二份画像。

G3 的消费前置条件是：任务由 G2 已提交、状态为 `queued`，资源类型和任务类型匹配，简历处于 `processing`，关联对象为 `ready`，且候选人归属链一致。任一条件不满足时，G3 不创建任务、不调用 G2 内部实现、不绕过 Repository 读取对象；只按既有安全失败/无副作用规则结束处理，具体对外失败分类仍使用既有 `parse_failure_code` 枚举。

### 4.2 API 责任

本模块沿用既有接口协议，不新增独立解析触发 API：

| 接口 | 本方案语义 |
| --- | --- |
| `POST /api/v1/resumes` | 上游上传接口返回 `201` 表示受控对象、简历和 G2 queued 任务交接已完成，`parse_status=processing`；不承诺解析成功。G3 消费已有任务，不创建第二个任务。 |
| `GET /api/v1/resumes` | 当前候选人自动查询自己的简历列表和 `parse_status`；成功项返回可用画像入口，失败项只返回允许暴露的 `failure_code`。 |
| `GET /api/v1/resumes/{resume_id}/profile` | 校验当前候选人归属；仅当简历为 `succeeded` 且画像已原子写入时返回画像；处理中、失败、不存在或越权均安全返回 `404`。 |

所有响应遵循 `{code,msg,data}`；不返回路径、对象键、简历正文、Markdown、模型原始响应、异常堆栈或自由文本失败原因。

### 4.3 G3 任务消费边界

G3 的任务入口只接受内部 `task_run_id`。入口不接受客户端请求，不接受路径、URL、对象键、文件正文、凭证或模型参数，也不通过 Celery Result Backend 读取业务结果。消费顺序固定为：

1. Dispatcher 读取已提交的 queued `AsyncTaskRun` 并投递同一 `task_run_id`；
2. Worker 通过 `AsyncTaskRepository` 领取当前任务的执行租约；
3. `DocumentParsingRepository` 按任务关联的资源 ID 重新校验候选人、简历、对象 `ready` 和任务版本；
4. 校验通过后才调用对象存储适配器、MinerU 和 Qwen；
5. 结果通过 `ResumeParseFinalizationService` 编排，并由 Repository 在同一事务中写入画像和简历/任务终态。

该入口是 G3 的 consumer 边界，不是 G2 的调用接口；任何需要 G2 内部 Service、Repository 实现或 G3 内部 Worker 的跨包调用均不属于本方案。

## 5. 状态机与事务设计

### 5.1 简历状态

```text
processing ──成功原子提交──> succeeded
processing ──确定性失败/重试耗尽──> failed
```

简历在排队、运行和可重试回排期间保持 `processing`。`CandidateProfile` 不定义独立状态；画像只有在简历成功事务中存在。

### 5.2 异步任务状态

```text
queued ──Dispatcher 投递──> queued（dispatched）
queued ──Worker 领取──> running
running ──可重试故障──> queued
running ──成功事务──> succeeded
running ──确定性失败/重试耗尽/卡死兜底──> failed
```

Worker 领取时以 Repository 行锁原子写入不可预测 `execution_token`、`started_at` 和执行租约。成功、失败、回排和终态清理均必须匹配 `task_run_id`、资源 ID、任务/资源类型、`status=running` 和当前令牌；迟到令牌或重复消息只返回无副作用结果。

### 5.3 成功事务

在一个 Repository 事务内锁定当前任务和简历，并完成：

1. 再次确认候选人归属、简历为 `processing`、任务为当前 `running`、令牌匹配；
2. 插入唯一 `candidate_profiles`（`resume_id` 唯一，`target_job_titles` 非空）；
3. 将简历置为 `succeeded`；
4. 将任务置为 `succeeded`，写入 `finished_at`，清理令牌和执行租约。

任一步骤失败，事务整体回滚，不允许出现“画像已写入但简历/任务仍处理中”或重复画像。

成功提交必须同时满足 `task_run_id`、资源类型/任务类型、简历 ID、`status=running` 和当前 `execution_token` 的条件围栏。若画像唯一约束冲突但已有完整成功结果，Repository 只能安全复用/收敛既有结果；迟到令牌、重复消息和已结束任务不得再次读取对象、调用模型或写入画像。

### 5.4 失败事务

确定性失败或重试耗尽时，在同一 Repository 事务内匹配当前令牌，将简历与任务置为 `failed`，写入允许暴露的 `parse_failure_code`，清理租约；不创建画像。可重试故障先释放当前令牌并将任务回排 `queued`，再由 Celery 按最大 2 次、指数退避和抖动策略重试。

Celery soft timeout 触发时，Worker 入口通过 Repository 关闭仍有效的当前租约并写入 `internal_error`，避免任务永久停留 `running/processing`；若 Worker 进程直接丢失，则依赖 late ack、Broker 重投递和过期租约接管，Dispatcher 对超过 10 分钟且租约过期的运行任务执行 `internal_error` 兜底。

G2 交接失败与 G3 执行失败严格隔离：G2 事务回滚并清理未引用临时对象；G3 失败只在已提交的 G2 资源上推进重试或失败终态，不回滚 `StoredFileObject`、`Resume` 或上传幂等关系。

## 6. 解析链路与失败映射

1. `DocumentParsingRepository` 按归属和对象状态读取正式 PDF，并在受限临时目录生成不可预测临时文件。
2. MinerU MCP stdio Bridge 只接收该临时文件，固定 `enable_ocr=false`，输出只进入内存 Markdown；不持久化中间文本。
3. Qwen Plus 通过 `response_format.type=json_schema` 和 `ResumeProfileExtractionV1.model_json_schema()` 生成结构化结果。
4. Pydantic 与业务规则校验结果；`target_job_titles` 去空、去重后至少有一个非空值，其余未知字段使用 `null` 或空数组，不猜测补全。
5. 成功或失败后立即清理临时文件；任何外部原始响应、Markdown、路径和异常正文均不进入日志或数据库。

| 故障 | 重试 | 终态 |
| --- | --- | --- |
| 对象暂不可读/缺失 | 是，最多 2 次 | `storage_unavailable` |
| MinerU 超时 | 是，最多 2 次 | `parser_timeout` |
| MinerU 网络/429/5xx | 是，最多 2 次 | `internal_error` |
| PDF 损坏、加密、扫描或无有效机器文本 | 否 | `file_unreadable` |
| Markdown 为空、画像 Schema/业务校验失败、缺少目标职位 | 否 | `schema_validation_failed` |

## 7. 安全、可观测性与边界

- 所有资源读取和画像查询均沿 `CurrentIdentity.candidate_id → Resume → CandidateProfile` 校验归属；越权和不存在资源统一安全 `404`。
- Service、Worker、Agent、Workflow 不直接访问 ORM Session、SQL 或本地文件；所有持久化和资源读取经过 Repository/适配器。
- 日志、审计和追踪只记录关联 ID、任务类型、版本、阶段、状态、耗时、重试次数和脱敏失败分类。
- 记录任务领取、回排、成功、失败、卡死兜底和重复/迟到消息的脱敏事件；不启用 Celery Result Backend。
- 运行就绪检查必须覆盖 PostgreSQL、Redis、Dispatcher、Worker、对象存储、MinerU 凭证和 Qwen 配置；外部依赖不可用不得伪造成功。

## 8. 回滚、兼容与发布边界

- 本变更沿用既有 `resumes`、`stored_file_objects`、`candidate_profiles`、`async_task_runs` 和 `parse_failure_code` 枚举，不新增 handoff 表、解析文本字段或外部技术依赖，不执行数据迁移。
- 代码发布失败或外部依赖不可用时，停止提交新成功结果；已成功画像不回滚、不重复生成；处理中任务按租约/兜底规则安全失败或回排。
- 上游资料准备模块必须先能通过固定契约交接有效 `ResumeParseRequestV1` 并创建/复用唯一 queued `AsyncTaskRun`；G3 不绕过上游创建资源，也不要求上游调用 G3 内部 Service/Worker。交接不可用时只阻塞跨模块联调，不改变 G3 已定义的消费方案。
- MVP 仅覆盖受控单份脱敏 PDF 演示，不声明 OCR、批量、高可用、运营后台、人工重跑或生产规模能力。

## 9. 方案评审清单

- [x] 方案边界与上游/下游责任已对应需求文档。
- [x] 技术路线均有阶段 2 真实证据或明确复用来源。
- [x] API、数据表、状态机、租约、重试和失败映射已固定。
- [x] 事务、幂等、迟到令牌和 Worker 丢失边界已定义。
- [x] 安全、日志脱敏、回滚和非目标已定义。
- [x] CHG-020/CHG-021 已联合锁定 `ResumeParseRequestV1@v1`，双方开发者已批准；CHG-021 阶段 1–3 已通过，阶段 4 尚未启动。

## 10. 阶段 3 门禁结论

本方案已依据阶段 1 需求裁决和阶段 2 `passed` 证据完成修订。方案固定了 G3 consumer 边界、任务入口、Repository 访问边界、解析链路、状态机、租约、幂等、失败隔离和回滚边界；没有新增外部技术能力，也没有修改已锁定的 `ResumeParseRequestV1@v1`。

本文件及 `change-record.md` 已完成阶段 3 交付物人工复核，CHG-021 阶段 3 已通过。阶段 4 任务拆分仍需按独立门禁启动和收口，阶段 5 编码尚未授权。
