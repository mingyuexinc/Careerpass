# 实现说明（阶段 5：G2 跨模块交接增量实现）

> 当前实现依据已通过的 CHG-020 阶段 1–4 门禁和锁定的 `ResumeParseRequestV1@v1`。本次只实现 G2 新边界，G3 解析执行链路不在本次代码修改范围内。

## 当前阶段 5 实现范围

- `CandidatePreparationService` 通过 Repository 暴露的事务上下文，协调正式简历、对象元数据、上传幂等关系和 queued `AsyncTaskRun` 在同一 PostgreSQL 事务中提交。
- `CandidatePreparationRepository.create_resume()` 不再自行开启或提交事务；事务由 G2 Service 统一协调，附加资料上传继续沿用原有独立事务。
- `AsyncTaskRepository.create_or_get_queued_resume_task()` 固定 `resume_parse`、`resume`、`task_version=v1` 和 `resume_parse:{resume_id}:v1` 幂等键；在同一事务中校验候选人归属、对象 `ready` 和简历 `processing` 状态，并使用 PostgreSQL 冲突忽略保证并发复用。
- `POST /api/v1/resumes` 在资源与 queued 任务可靠提交后返回 `201 / UPLOAD_ACCEPTED`、`resume_id` 和 `parse_status=processing`；不表示 MinerU、Qwen 或画像解析成功。
- G2 不调用 G3 Service、Dispatcher、Worker、MinerU 或 Qwen；对象失败、事务失败和未引用临时对象仍通过脱敏错误和清理边界处理。

## 当前验证记录

- `uv run pytest tests/unit -q --no-cov`：全部单元测试通过。
- `uv run ruff check`：本次修改文件全部通过。
- 阶段 6 已在隔离 Docker Compose PostgreSQL/Redis 环境中完成 6 项真实集成测试；详细结果见 `06-verification/test-report.md`。
- 阶段 5 实现证据已记录，开发者已完成阶段 5 门禁确认并批准通过。阶段 6 单元测试、阶段 7 代码评审和阶段 8 跨模块真实联调属于后续门禁，不是阶段 5 的通过前置条件。

## 阶段 5 门禁复核结果

按《开发流程规范》，阶段 5 的通过条件是：阶段 4 已批准的任务均已实现，并且实现未违反红线和架构边界。当前文档已记录 G2 事务协调、任务创建/复用、上传受理响应和边界隔离的实现证据。复核确认本阶段不缺少 MinerU、Qwen 或真实 PostgreSQL/Redis 联调前置条件，开发者已完成以下收口确认：

1. 阶段 4 任务清单中的实现项已逐项完成，没有新增未裁定的范围、契约、数据字段、状态机或跨模块责任。
2. Repository、权限归属、统一响应、敏感信息脱敏和事务边界等红线均符合要求，阶段 5 的 `approved_by`、`approved_at` 和批准说明已写入 `00-governance/stage-gates.yaml`。

上述确认已完成，阶段 5 已标记为 `passed`；阶段 6 及以后再分别补充测试、评审和真实联调证据。

## 当前边界修订（权威记录）

- `CandidatePreparationRepository` 仅持久化候选人上传对象和资料元数据；G2 Service 通过独立的 `AsyncTaskRepository` 提交固定 `ResumeParseRequestV1@v1` 对应的 queued 任务。
- 候选人资料 API 的依赖装配不再把 `DocumentParsingRepository` 注入候选人资料 Service；文档解析继续由独立模块负责。
- 正式简历上传响应恢复为锁定方案要求的 `parse_status=processing` 和“上传已受理，正在解析简历”；附加资料不创建解析任务，仍返回“上传成功”。
- 保留数据库中的解析字段、`candidate_profiles` 和 `async_task_runs`，不执行破坏性迁移；这些结构由文档解析模块使用。
- 历史边界测试和覆盖率记录保留为迁移前证据；本次阶段 5 当前验证以本文件“当前验证记录”和后续阶段 6 报告为准。

- `careerpass-backend/alembic/versions/20260727_0003_candidate_preparation.py` 创建资料、画像、对象和异步任务数据结构。
- `app/infrastructure/storage/` 提供不透明键本地受控读写；候选人资料准备和文档解析分别通过各自 Repository 管理其业务边界。
- `app/api/v1/candidate_preparation.py` 提供简历和附加资料接口；画像查询由文档解析路由负责，所有操作通过当前候选人身份校验。
- 外部 MinerU/Qwen 实际 Worker 调用和隔离环境外部集成待真实凭证可用后完成；不得用伪造响应替代验收。
- 上传去重修复：Repository 现在显式返回底层对象是否新建；同一幂等键重放或不同资源复用既有内容摘要时，Service 删除本次暂存的未引用物理对象。幂等重放同时校验显示名与内容摘要，避免同一键覆盖不同文件。
- 对象生命周期：`ObjectStorageRepository` 使用行锁和引用复核领取超过 1 小时的 `writing/ready` 无引用对象，状态转换为 `deleting` 后删除物理文件和目录记录；物理删除失败恢复为原状态。应用生命周期注册独立的每小时清理循环，关闭时安全取消。
- 子任务 3（简历/附加资料 API 真实集成验证）：上传成功响应现在显式使用协议定义的 `201` 业务码；正式简历返回“上传已受理，正在解析简历”，附加资料返回“上传成功”。列表和画像查询仍维持通用 `200 / success`，避免将上传语义误用于读取接口。
# 子任务 4：可靠投递与执行租约

- `TaskDispatcher` 是独立进程，不是 FastAPI 生命周期任务，也不是 Celery Beat。它锁定 queued 任务记录，分配一个持久化 Celery 任务 ID 和短时发布租约，只有确认消息成功发布到代理后才标记发布完成。
- 发布中断时保留租约，租约到期后使用同一个任务 ID 重新发布。PostgreSQL 是权威数据源，Redis 仅作为消息代理。
- `AsyncTaskExecutionService` 通过 `AsyncTaskRepository` 获取新的不可预测执行令牌。后续解析 Worker 必须使用该令牌保护重试、结果和终态写入。
- Celery 不使用结果后端，启用延迟确认、Worker 丢失时拒绝消息、预取数量为 1，Redis 可见性超时为 300 秒。MinerU/Qwen 解析不属于本子任务。
# 子任务 5：MinerU MCP 适配器

- `MineruMcpAdapter` 只接受未来持有租约的 Worker 提供的 PDF 字节。它写入随机临时 `.pdf` 文件，只调用 MCP 工具 `parse_documents`，在内存中规范化 Markdown，并在所有执行路径清理临时目录。
- `MineruStdioClient` 是 MVP 客户端。它启动同机官方 `uvx mineru-open-mcp` Bridge，仅在子进程中将 `MINERU_API_KEY` 映射为 `MINERU_API_TOKEN`，抑制 Bridge 标准错误输出，并按已验证的 `file_sources=[local_pdf_path]` 契约调用，关闭 OCR（`enable_ocr=false`）。
- 适配器不接受候选人路径、客户端/Agent/模型提供的 URL、模型拼接的参数或输出位置；不持久化或记录 MCP 原始响应、文件路径、临时访问 URL 或凭证。
- 安全失败分类为：超时映射为 `parser_timeout`（可重试）；连接失败、429 或 5xx 映射为 `internal_error`（可重试）；结果格式错误、不可读或为空映射为 `file_unreadable`（终态失败）。
- `MineruStreamableHttpClient` 仅保留为有条件启用的远程实现。此前尝试的远程 Bearer 会话在工具发现时返回 HTTP 401，因此未启用为 MVP Worker 实现。

# 子任务 6：Qwen 结构化画像适配器

- `QwenProfileAdapter` 使用 `DASHSCOPE_API_KEY`、显式配置的 `QWEN_BASE_URL` 和 `QWEN_MODEL=qwen-plus`，调用配置的 DashScope OpenAI 兼容 `chat/completions` 接口。
- 请求使用严格的 `response_format.type=json_schema`，Schema 直接由 `ResumeProfileExtractionV1` 生成；普通 JSON 模式无法阻止额外字段或嵌套值结构错误，因此不满足要求。
- 适配器只接收内存中的 MinerU Markdown，只返回经过 Pydantic 校验的 `ResumeProfileExtractionV1`；不保留 Prompt、提供方原始响应、令牌或请求诊断信息。
- 超时映射为 `parser_timeout`；传输错误、429 和 5xx 映射为 `internal_error`；JSON 格式错误或 Schema/业务校验失败映射为 `schema_validation_failed`。

# 子任务 7：解析终态原子写入（历史证据，归属 CHG-021）

- `CandidatePreparationRepository` 中历史解析终态记录仅作为证据保留；当前 G2 代码不拥有 G3 的租约保护终态写入。
- 受租约保护的成功/失败路径由 `DocumentParsingRepository` 和 `ResumeParseFinalizationService` 负责，本次 G2 实现不修改这些路径。
- 当前 G2 变更只创建或复用持久化 queued 任务，不写入 `CandidateProfile`、解析失败码、执行租约或解析终态。

# 子任务 8：模块边界修复与版本化契约（历史记录，当前边界已迁移）

- `ResumeParseRequestV1` 仍是候选人资料准备到文档解析之间固定且禁止额外字段的契约。当前 G2 Service 通过 `AsyncTaskRepository` 创建或复用固定 queued 任务；G3 消费既有任务，不再创建另一个任务。
- `CandidatePreparationRepository` 不再导入 `AsyncTaskRun`、`CandidateProfile`、解析失败类型或画像提取 Schema；它只负责候选人资料、简历、上传幂等以及受控列表/状态。
- `DocumentParsingRepository` 负责受控画像读取、租约保护的画像/终态写入以及未来 Worker 的资源读取；G2 上传代码不调用它。
- 对外稳定的 `GET /api/v1/resumes/{resume_id}/profile` 路由由文档解析路由注册，并通过 `DocumentParsingService` 处理；继续保留当前候选人归属过滤和安全 `404` 行为。

# 子任务 9：简历解析 Worker 编排

- `ResumeParseWorkerService` 只协调带类型且由 Repository 支持的端口。读取简历前先领取执行租约；缺少租约或租约已过期时不产生副作用并直接忽略。
- `DocumentParsingRepository.read_resume_for_processing` 只授权读取绑定到 `ready` 对象且处于 `processing` 状态的简历，然后使用受控存储读取器；缺失、无效或不可读的存储映射为 `storage_unavailable`，不泄露路径或对象键。
- 固定 Celery 任务 `careerpass.resume_parse` 只接受 `task_run_id`。它根据 Worker 配置构造已批准的 stdio MinerU 和 Qwen 适配器，在内存中处理 PDF 字节和 Markdown，并将所有终态写入委托给 `ResumeParseFinalizationService`。
- `parser_timeout`、`internal_error` 和 `storage_unavailable` 在有界指数退避/抖动重试前释放匹配的执行租约。`file_unreadable`、`schema_validation_failed` 或重试耗尽时调用文档解析原子失败边界。不引入 Celery 结果后端。

# 子任务 10：候选人资料准备验收与收口

- 候选人资料准备仍限于上传、幂等、受控对象存储以及候选人范围内的资源/状态查询；不导入或拥有画像持久化、文档读取、MinerU/Qwen 调用、Worker 执行或下游准入决策。
- 当前阶段 5 单元测试证明 G2 Service 在上传事务中调用任务 Repository，并返回 `processing`；真实隔离运行时测试仍待阶段 6/8 环境门禁开启后验证。
- 集成验收必须断言上传提交后存在固定 `resume_parse`、`resume`、`v1`、`queued` 任务，且相同幂等请求只复用同一简历和任务。
- 该交接仍是 G2 模块边界终点：G2 不启动或检查 Worker，也不断言 MinerU、Qwen、画像或解析终态；这些由 CHG-021 后续阶段负责。
