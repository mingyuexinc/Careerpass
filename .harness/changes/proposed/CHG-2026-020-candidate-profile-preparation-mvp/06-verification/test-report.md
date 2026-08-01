# 子任务 0：资料上传切片验收报告

## 结果

- Ruff 静态检查：通过。
- 单元测试：79 项通过，覆盖率 81.12%。
- 隔离 PostgreSQL/Redis 集成测试：2 项通过。

## 覆盖证据

- 同一 `Idempotency-Key` 与相同文件重放首次资源 ID。
- 不同幂等键上传相同 PDF 创建两个简历资源、复用一个内部文件对象。
- 重放与内容去重产生的临时物理对象均被删除；受控对象目录仅保留一个被引用文件。
- 数据库中候选人范围内不存在无简历引用的本次对象记录。

## 结论

子任务 0 已通过，不包含 Dispatcher、解析 Worker、画像或下游模块前置条件校验等后续任务。

## 子任务 1：资料数据层与迁移验证

- 迁移将资料与任务状态收敛到 PostgreSQL 枚举，避免自由字符串写入。
- 增加文件大小、画像年限、任务终态与失败原因约束；增加待投递部分索引和文件对象 `updated_at` 触发器。
- 隔离 PostgreSQL 执行两次 `upgrade → downgrade → upgrade`；`users`、`candidates` 与五张资料表、三个更新时间触发器、五项关键约束均通过目录查询验证。
- ORM 使用同名 PostgreSQL 枚举，上传集成测试确认不会出现绑定类型不匹配。

## 子任务 2：对象存储生命周期

- 清理按“行锁领取、引用复核、`deleting`、物理删除、目录删除”顺序执行；异常删除恢复为可重试状态。
- 应用启动后运行独立每小时清理循环，关闭时取消；未使用 Celery Beat 或后续 Dispatcher。
- 单元测试覆盖清理成功、物理删除失败恢复、批次边界与调度入口。
- 隔离 PostgreSQL 集成测试验证：过期无引用对象及物理文件删除；仍被候选人资料引用的共享对象保持不变。

## 子任务 3：简历/附加资料 API 真实集成验证

### 结果

- Ruff 静态检查：通过。
- 单元测试：85 项通过。
- 隔离 PostgreSQL、Redis 与本地对象存储集成测试：4 项通过。

### 覆盖证据

- 正式简历上传返回 HTTP 与响应体 `201`、`上传已受理，正在解析简历` 及 `processing` 初始状态；同一幂等键重放复用原简历资源。
- 同一幂等键提交不同文件返回安全 `409`，非法扩展名/MIME 文件返回安全 `400`。
- 两个已认证候选人的简历与附加资料列表相互隔离；其他候选人查询简历画像得到统一安全 `404`。
- Markdown 附加资料上传及类型过滤返回 HTTP 与响应体 `201`、`上传成功`；列表项不包含 `storage_key` 或文件正文。

### 发现与修复

- 初次真实集成执行发现附加资料端点的 HTTP 状态为 `201`，但响应体仍为默认 `200 / success`。已将响应工厂扩展为显式成功业务码，并将上传端点绑定到协议定义的受控消息；修复后完整集成套件通过。

### 结论

子任务 3 已通过。该结论仅覆盖上传与读取 API 的真实本地依赖验证；不包含后续 Dispatcher、Worker、MinerU/Qwen 解析或外部集成验收。

### 变更包校验边界

- 已执行 `python .harness/changes/tools/validate_changes.py`。仓库级校验当前因既有 `CHG-2026-019-upload-idempotency-contract` 缺少 `change.yaml` 与 `01-analysis/impact-analysis.md` 失败；未修改该独立变更包。本 CHG-020 的本次实现、单元测试和真实本地集成验证均已完成。
# Subtask 4: reliable enqueue, Dispatcher, and execution leases

## Result

- Ruff passed; unit suite: 85 passed.
- Isolated PostgreSQL, Redis, and local object-storage integration suite: 5 passed.

## Evidence

- A persisted `async_task_runs` record was published to a real isolated Redis Celery queue, then marked dispatched in PostgreSQL.
- Repeated dispatcher iterations did not re-publish confirmed work; dispatcher publication leases make interrupted publication safely retryable with the same Celery task ID.
- One running task accepted one execution lease. A late worker holding its former token could not release the newer lease.
- An expired running lease older than ten minutes was atomically changed to `failed / internal_error` with the linked processing resume.

## Boundary

This subtask supplies dispatch and lease infrastructure only. It does not run MinerU/Qwen, read file content, or write a candidate profile; the later parsing Worker must use `AsyncTaskExecutionService` before any business-side effect.
# Subtask 5: MinerU MCP parsing adapter

## Result

- Ruff passed; full suite: 113 passed, 6 explicitly skipped, total coverage 80.00%.
- Adapter and client tests verify opaque temporary PDF input, temporary-file cleanup, controlled Markdown extraction, output-path containment, stdio environment isolation, verified `file_sources` contract, OCR disabled, and failure classification.

## External dependency gate

- `MINERU_API_KEY` was read from the local system environment only for the explicitly enabled test and was never printed or persisted.
- 2026-07-27: `uvx mineru-open-mcp` stdio Bridge completed MCP `initialize` and `tools/list`; the discovered tools were `parse_documents` and `get_ocr_languages`.
- 2026-07-27: with `RUN_EXTERNAL_INTEGRATION_TESTS=true`, the controlled desensitized `resume_1.pdf` completed a real `parse_documents` call through the stdio Bridge. The test asserted only non-empty Markdown and an empty task temporary directory; it did not log the source, extracted content, paths, token, or raw provider response.
- This passes MinerU MCP connectivity and text-extraction acceptance for subtask 5. It does not claim Qwen profiling, worker lease/result persistence, or the full candidate-profile external integration chain.

# Subtask 6: Qwen structured profile adapter

## External technology prevalidation

- 2026-07-27: using the Worker-equivalent Python runtime and machine-scoped `DASHSCOPE_API_KEY`, a fixed non-personal sample was sent to `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` with `model=qwen-plus`.
- The endpoint returned HTTP 200 and a JSON object. No token, prompt, or provider response was recorded.
- Initial ordinary JSON mode produced JSON that failed `ResumeProfileExtractionV1` validation. The adapter correctly rejected it with `schema_validation_failed`; no persistence path exists in this subtask.
- The selected MVP contract was therefore changed to strict `json_schema`, generated from the Pydantic model, and then revalidated with a real call.

## Result

- Unit tests cover request constraints, strict Pydantic validation, empty input, malformed/provider output, timeout, 429 and 5xx classification.
- With `RUN_EXTERNAL_INTEGRATION_TESTS=true`, the final adapter sent fixed desensitized Markdown to Qwen Plus and received a profile that passed `ResumeProfileExtractionV1` validation.
- Final regression gate: Ruff passed; `121 passed, 7 skipped`; total coverage `80.46%`.
- This passes Qwen connectivity and structured-output acceptance for subtask 6. It does not claim the later leased Worker, atomic profile persistence, or combined MinerU→Qwen full-chain acceptance.

# Subtask 7: atomic parse terminal states

## Result

- Isolated PostgreSQL/Redis integration test passed after creating real candidate resumes and obtaining real database execution leases.
- Final regression gate: Ruff passed; `125 passed, 8 skipped`; total coverage `80.14%`.
- Success wrote one validated profile and set both `resumes.parse_status` and `async_task_runs.status` to `succeeded` in one Repository transaction, then cleared the execution lease.
- A later failure attempt using the completed lease was rejected without changing persisted data.
- Failure wrote the same controlled `schema_validation_failed` enum to resume and task, set both states to `failed`, cleared the execution lease, and left no `candidate_profiles` row.

## Boundary

- This subtask implements only lease-guarded terminal persistence. The next Worker orchestration subtask must claim a lease, invoke MinerU and Qwen, choose retry versus terminal failure, and call this boundary; it must not write ORM rows directly.

# Subtask 8: module boundary remediation and versioned contract

## Result

- Ruff passed.
- Full regression: `128 passed, 8 skipped`; total coverage `80.39%`.
- The eight skipped tests are explicitly gated real integration/external-integration tests. Docker is unavailable in the current execution environment, so no isolated PostgreSQL/Redis integration result is claimed for this subtask.

## Evidence

- Candidate preparation submits only extra-field-forbidden `ResumeParseRequestV1`; document parsing validates the candidate/resume relation before creating the fixed `v1` parse task in the existing transaction.
- Candidate preparation no longer imports or accesses `CandidateProfile`, `AsyncTaskRun`, parse failure types, profile schemas, profile query, or terminal-write methods.
- Document parsing owns profile queries, resource reads and lease-guarded terminal writes. The existing profile URL remains stable and uses the document-parsing router/service with candidate ownership filtering.

## Boundary

- This subtask intentionally does not register or execute a parsing Worker. Worker lease claim, controlled file read, MinerU/Qwen orchestration and retry policy remain the next subtask.

# Subtask 10: candidate-preparation acceptance and closure

## Result

- Ruff passed.
- Full regression: `135 passed, 8 skipped`; total coverage `81.73%`.
- The eight skipped tests are explicit PostgreSQL/Redis/Celery or external-provider gates. Docker is unavailable in the current environment, so no isolated real-dependency execution is claimed.

## Evidence

- Candidate preparation integration coverage verifies formal-resume upload, idempotent replay and conflict behavior, shared-object reuse without orphan objects, safe response fields, candidate isolation, and the safe `404` profile query behavior.
- `test_candidate_preparation_parse_handoff.py` verifies that one newly created formal resume submits exactly one frozen `ResumeParseRequestV1` while its creation transaction remains active.
- The Dispatcher integration scenario asserts that the persisted hand-off is the fixed `resume_parse` / `resume` / `v1` queued task before reliable publication. It verifies Dispatcher recovery behavior only; it neither starts nor asserts a parsing Worker.

## Boundary and closure

- Subtask 10 is accepted at the reliable hand-off from candidate preparation to document parsing. It does not own or validate file reads, Worker orchestration, MinerU, Qwen, profile persistence, or terminal parse states.
- The end-to-end parsing and external-dependency acceptance remains subtask 11. This report intentionally does not use the existing Worker unit tests or earlier adapter prevalidation as a substitute for that gate.
- Change-package validation remains blocked by the pre-existing independent `CHG-2026-019-upload-idempotency-contract` package missing `change.yaml` and `01-analysis/impact-analysis.md`; no files in that package were changed.

# Subtask 9: resume parsing Worker orchestration

## Result

- Ruff passed.
- Full regression: `134 passed, 8 skipped`; total coverage `80.65%`.
- The eight skipped tests are explicit integration/external-integration gates. Docker is unavailable in the current environment, so no PostgreSQL/Redis/Celery Worker integration result is claimed.

## Evidence

- `careerpass.resume_parse` is registered on the dedicated Worker application and accepts only a UUID `task_run_id`.
- Every execution claims a database execution lease before controlled file access. Duplicate or late deliveries with no claimable lease return with no side effect.
- The Repository authorizes a `processing` resume and a `ready` stored object before it invokes the opaque-key storage reader; object access failures become retryable `storage_unavailable` without recording object keys, paths, source bytes, Markdown, credentials, or provider responses.
- Retryable MinerU/Qwen/storage failures release the matching lease before a bounded Celery exponential-backoff/jitter retry. Deterministic failures and retry exhaustion call only the lease-guarded terminal boundary.
- Unit tests cover success, duplicate delivery, retry release, deterministic failure, retry exhaustion, Worker task registration, and runtime port composition.

## Boundary

- The Worker implementation is ready for isolated Broker/Worker integration verification, but this task does not claim the real MinerU → Qwen end-to-end acceptance reserved for subtask 10.
# 边界修订验证记录（当前）

- 执行命令：`uv run pytest -q`
- 结果：`129 passed, 9 skipped`（以本次运行输出为准）
- 覆盖率：`81.16%`，达到规范要求的 80%。
- 边界专项：候选人资料上传 Repository、Schema、API 和依赖装配测试通过。
- 解析相关测试仍保留在独立解析链路中，未作为候选人资料上传验收条件。
- 静态检索确认候选人资料 Repository/Service/Schema/API 未再引用解析请求提交、解析状态或解析失败字段。
