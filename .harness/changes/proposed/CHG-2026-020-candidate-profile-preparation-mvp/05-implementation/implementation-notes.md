# 实现说明

- `careerpass-backend/alembic/versions/20260727_0003_candidate_preparation.py` 创建资料、画像、对象和异步任务数据结构。
- `app/infrastructure/storage/` 提供不透明键本地受控读写；候选人资料准备和文档解析分别通过各自 Repository 管理其业务边界。
- `app/api/v1/candidate_preparation.py` 提供简历和附加资料接口；画像查询由文档解析路由负责，所有操作通过当前候选人身份校验。
- 外部 MinerU/Qwen 实际 Worker 调用和隔离环境外部集成待真实凭证可用后完成；不得用伪造响应替代验收。
- 上传去重修复：Repository 现在显式返回底层对象是否新建；同一幂等键重放或不同资源复用既有内容摘要时，Service 删除本次暂存的未引用物理对象。幂等重放同时校验显示名与内容摘要，避免同一键覆盖不同文件。
- 对象生命周期：`ObjectStorageRepository` 使用行锁和引用复核领取超过 1 小时的 `writing/ready` 无引用对象，状态转换为 `deleting` 后删除物理文件和目录记录；物理删除失败恢复为原状态。应用生命周期注册独立的每小时清理循环，关闭时安全取消。
- 子任务 3（简历/附加资料 API 真实集成验证）：上传成功响应现在显式使用协议定义的 `201` 业务码；正式简历返回“上传已受理，正在解析简历”，附加资料返回“上传成功”。列表和画像查询仍维持通用 `200 / success`，避免将上传语义误用于读取接口。
# Subtask 4: durable dispatch and execution leases

- `TaskDispatcher` is a standalone process, not a FastAPI lifecycle task and not Celery Beat. It locks queued rows, assigns one durable Celery task ID and a short publication lease, then confirms only after broker publication succeeds.
- Publication interruption leaves the lease to expire and be republished with the same task ID. PostgreSQL remains the authority; Redis is broker-only.
- `AsyncTaskExecutionService` acquires a fresh unpredictable execution token through `AsyncTaskRepository`. A future parsing worker must use that token to guard retry, result, and terminal writes.
- Celery uses no result backend, late acknowledgements, reject-on-worker-lost, prefetch one, and a 300-second Redis visibility timeout. MinerU/Qwen parsing remains outside this subtask.
# Subtask 5: MinerU MCP adapter

- `MineruMcpAdapter` accepts only PDF bytes supplied by a future leased Worker. It writes a random temporary `.pdf`, calls only MCP tool `parse_documents`, normalizes Markdown into memory, and removes the temporary directory on every path.
- `MineruStdioClient` is the MVP client. It launches the official same-machine `uvx mineru-open-mcp` Bridge, maps `MINERU_API_KEY` to `MINERU_API_TOKEN` only in the child process, suppresses Bridge stderr, and calls the verified `file_sources=[local_pdf_path]` contract with `enable_ocr=false`.
- The adapter does not accept candidate paths, client/Agent/model-provided URLs, model-composed parameters, or output locations. It never persists or logs raw MCP responses, file paths, temporary access URLs, or credentials.
- Safe failure classes map timeout to `parser_timeout` (retryable), connectivity/429/5xx to `internal_error` (retryable), and malformed, unreadable, or empty results to `file_unreadable` (terminal).
- `MineruStreamableHttpClient` remains a conditional remote implementation only. The previously attempted remote Bearer session returned HTTP 401 during tool discovery and is not enabled for MVP Worker use.

# Subtask 6: Qwen structured profile adapter

- `QwenProfileAdapter` calls the configured DashScope OpenAI-compatible `chat/completions` endpoint using `DASHSCOPE_API_KEY`, explicit `QWEN_BASE_URL`, and `QWEN_MODEL=qwen-plus`.
- The request uses strict `response_format.type=json_schema`, generated directly from `ResumeProfileExtractionV1`; ordinary JSON mode is insufficient because it cannot prevent extra fields or incorrectly shaped nested values.
- The adapter receives only in-memory MinerU Markdown and returns only a Pydantic-validated `ResumeProfileExtractionV1`. It retains no prompt, raw provider response, token, or request diagnostic.
- Timeouts map to `parser_timeout`; transport, 429 and 5xx failures map to `internal_error`; malformed JSON or schema/business validation failures map to `schema_validation_failed`.

# Subtask 7: atomic parse terminal states

- `CandidatePreparationRepository` now owns lease-guarded terminal writes. Its success path atomically locks the matching running `async_task_runs` and `resumes` rows, creates the sole `candidate_profiles` record, and changes both resource and task to `succeeded`.
- Its failure path uses the identical `task_run_id + resume_id + execution_token` guard, writes only an enum `failure_code`, and changes both resource and task to `failed` without creating a profile.
- Both paths clear `execution_token` and `execution_lease_expires_at`, and reject duplicate or late workers without any side effect. `ResumeParseFinalizationService` exposes this Repository-only boundary to the later Worker implementation.

# Subtask 8: module boundary remediation and versioned contract

- `ResumeParseRequestV1` is the fixed, extra-field-forbidden contract from candidate preparation to document parsing. Candidate preparation creates the candidate-owned resume and submits only this request; the document-parsing Repository validates the candidate/resume relation and persists the fixed `v1` task in the same database transaction.
- `CandidatePreparationRepository` no longer imports `AsyncTaskRun`, `CandidateProfile`, parsing failure types, or profile extraction schemas. It owns only candidate documents, resumes, upload idempotency, and controlled lists/statuses.
- `DocumentParsingRepository` now owns parse-request persistence, controlled profile reads, lease-guarded profile/terminal writes, and resource reads for the future Worker. `ResumeParseFinalizationService` depends exclusively on this boundary.
- The externally stable `GET /api/v1/resumes/{resume_id}/profile` route is registered by the document-parsing router and resolved through `DocumentParsingService`; it retains current-candidate ownership filtering and the safe `404` behavior.

# Subtask 9: resume parsing Worker orchestration

- `ResumeParseWorkerService` coordinates only typed, Repository-backed ports. It claims an execution lease before the resume is read; missing or late leases are ignored without a side effect.
- `DocumentParsingRepository.read_resume_for_processing` authorizes only a `processing` resume bound to a `ready` object, then uses the controlled storage reader. It maps missing, invalid or unreadable storage to `storage_unavailable` without leaking a path or object key.
- The fixed Celery task `careerpass.resume_parse` accepts only `task_run_id`. It constructs the approved stdio MinerU and Qwen adapters from worker configuration, keeps PDF bytes and Markdown in memory, and delegates all terminal writes to `ResumeParseFinalizationService`.
- `parser_timeout`, `internal_error`, and `storage_unavailable` release the matching execution lease before bounded exponential-backoff/jitter retry. `file_unreadable` and `schema_validation_failed`, or retry exhaustion, call the atomic document-parsing failure boundary. No Celery Result Backend is introduced.

# Subtask 10: candidate-preparation acceptance and closure

- Candidate preparation remains limited to upload, idempotency, controlled object storage and candidate-scoped resource/status queries. It does not import or own profile persistence, document reads, MinerU/Qwen calls, Worker execution, or downstream admission decisions.
- A focused repository test proves that creating a formal resume invokes exactly one extra-field-forbidden `ResumeParseRequestV1` while the resume-creation transaction is still active.
- The isolated-runtime dispatcher test now asserts that the request persisted at upload has the fixed `resume_parse` task type, `resume` resource type, `v1` task version and `queued` initial state before Dispatcher publication.
- The hand-off is deliberately the module terminal boundary: acceptance does not start or inspect a Worker and does not assert MinerU, Qwen, profile, or parsing terminal outcomes. Those are owned by the document-parsing acceptance in subtask 11.
