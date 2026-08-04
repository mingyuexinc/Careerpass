# 方案设计（修订版）

> 适用变更：CHG-2026-020 候选人资料准备 MVP。本文以已通过的需求分析与外部技术能力预验证为准；下方“历史设计（废止）”仅保留旧记录，不属于当前实现范围。

## 目标与非目标

### 目标

- 为已认证用户提供正式简历及候选人资料文件的上传闭环。
- 在上传时完成文件类型、大小、内容特征、候选人归属和幂等校验。
- 通过本地对象存储和 Repository 持久化文件元数据，支持按当前用户查询自己的资源元数据。
- 在对象达到 `ready` 且 G2 事务提交时，持久化固定的 `ResumeParseRequestV1` 交接记录/排队占位，使 `POST /api/v1/resumes` 能返回 `201 / UPLOAD_ACCEPTED` 和 `parse_status=processing`。
- 统一返回 `{code, msg, data}`，不暴露本地路径、存储键或敏感原文；交接只允许资源 ID、候选人归属和 `task_version=v1`。

### 非目标

本模块不调用解析 Service、Dispatcher、Celery Worker、MinerU 或 Qwen，不维护候选人画像和解析终态。正式简历完成上传、归属校验且对象为 `ready` 后，G2 只在自身 Repository 事务内写入固定的 `ResumeParseRequestV1` 交接记录/排队占位；这不是调用 G3 的 Service、Dispatcher 或 Worker。G3 从该固定交接开始消费并负责解析任务执行、解析终态和画像写入；G2 不以 G3 的解析成功或失败作为上传事务的回滚条件。

## 方案与数据流

```text
CurrentIdentity
    -> API 鉴权与 multipart 校验
    -> 本地对象存储临时写入（扩展名/MIME/魔数/大小校验）
    -> G2 Repository 事务（StoredFileObject + Resume/CandidateDocument + 上传幂等记录）
    -> 同一事务写入固定 ResumeParseRequestV1 交接记录/排队占位
    -> 统一响应（resume_id、parse_status=processing、脱敏元数据）
    -> G3 后续消费交接记录并独立执行解析
```

文件系统与 PostgreSQL 不具备跨系统原子事务，因此采用“先写临时对象、再在 Repository 事务中提交元数据与交接记录”的方式。G2 事务必须保证 `StoredFileObject`、正式简历、上传幂等关系和 `ResumeParseRequestV1` 交接记录/排队占位一致；事务失败时删除未被引用的对象，或将其交给受控清理任务，任何时点都不向客户端返回未提交资源。G3 后续解析失败不回滚已提交的 G2 资料资源，只由 G3 记录解析失败终态。幂等键重放返回原资源及 `processing`，参数不一致返回 409；所有查询和修改均以当前用户/候选人归属为条件。

## 业务闭环与技术能力映射

| 用户可见结果 | 业务模块 | 技术能力 | 状态 | 本次方式 | 启用条件 | 验收门槛 |
|---|---|---|---|---|---|---|
| 简历上传并受控交接、资料可查询 | G2 候选人资料准备 | CurrentIdentity、Repository/PostgreSQL、本地对象存储 | 已验证/复用 | 同步 HTTP + G2 Repository 事务写入交接记录/排队占位 | 已认证用户、对象 `ready`、G2 事务可提交 | `201 / UPLOAD_ACCEPTED`、`processing`、交接字段白名单、重放幂等、归属隔离、失败清理、统一响应 |
| 解析任务执行、解析终态和画像写入 | G3 文档解析 | Dispatcher/Celery/Redis/MinerU/Qwen 等 | 由 CHG-021 管理 | G3 消费 G2 固定交接记录 | G2 交接已提交 | 不作为 CHG-020 G2 事务成功条件 |

## 工作流/任务契约

本模块不启用 Agent、Workflow、Dispatcher、Celery 或其他解析执行任务。G2 在受控资料事务内完成上传、对象就绪校验、业务资源持久化、上传幂等和 `AsyncTaskRun(status=queued)` 创建/复用；`ResumeParseRequestV1` 只有 `candidate_id`、`resume_id`、`task_version="v1"` 三个字段，采用 `extra="forbid"`，不传递正文、路径、对象键、模型参数或自由指令。G2 不调用文档解析 Service，不直接投递 Worker。G3 只消费 G2 已提交的 queued 任务，并负责后续重试、解析终态和画像写入。

## 延期的平台化项

云对象存储、多租户通用文件中心、批量上传、版本管理、生命周期管理后台、跨模块文件读取 SDK，以及解析任务编排均延期到相应独立变更包。

## 接口、状态机与权限

- `POST /api/v1/resumes`：认证用户上传 PDF 简历；完成 G2 事务和固定交接记录/排队占位写入后返回 `201 / UPLOAD_ACCEPTED`，`data` 至少包含 `resume_id` 和 `parse_status=processing`，不表示 G3 已解析成功。
- `GET /api/v1/resumes`：分页返回当前候选人自己的简历元数据及受控解析状态；解析状态由 G3 后续推进，G2 不直接写入解析终态。
- `POST /api/v1/candidate_documents`：认证用户上传允许的 PDF/Markdown/JPG/JPEG 资料，支持类型、名称和幂等键。
- `GET /api/v1/candidate_documents`：按当前用户及资料类型查询元数据。
- 附加资料上传只形成 G2 自有资料记录，不创建 `ResumeParseRequestV1`，也不进入 G3 解析交接。
- 所有接口遵循 `{code,msg,data}`；未认证返回 401，归属不符按资源不存在处理，不接受仅凭资源 ID 越权访问。

对象内部状态仅用于存储可靠性：`writing -> ready -> deleting`。正式简历只有在对象 `ready` 且 G2 Repository 事务提交（含交接记录/排队占位）后才对外返回 `UPLOAD_ACCEPTED`。`processing` 是交接受理时的受控业务状态；G2 不拥有 `processing -> succeeded/failed` 的解析迁移，G3 负责后续状态机、失败原因和画像结果。

### 交接契约与幂等约束

- `ResumeParseRequestV1` 固定字段为 `candidate_id`、`resume_id`、`task_version="v1"`；未知字段、路径、URL、对象键、正文、模型参数和自由指令一律拒绝。
- Repository 必须同时校验 `resume_id` 属于当前 `candidate_id`，且关联对象存在并为 `ready`；校验失败不得创建交接记录/排队占位，也不得暴露内部定位信息。
- 相同候选人、简历和 `v1` 的重复交接只保留一个有效交接/任务占位；数据库唯一约束与 Repository 复用逻辑共同保证幂等。
- 相同候选人、接口和幂等键配合相同文件摘要/名称重放返回原 `resume_id` 与 `processing`；同键不同摘要或名称安全返回 409，不覆盖既有资源。

### 层级与事务边界

- API 负责认证、输入和统一错误映射；Service 负责业务编排和状态决策；所有简历、对象、幂等和交接读写均经 Repository，Service 不直接访问 ORM Session 或 SQL。
- G2 的数据库事务覆盖 `StoredFileObject`、`Resume`、上传幂等关系和固定交接记录/排队占位；事务提交前不返回资源。对象写入失败、归属失败、字段/状态校验失败或事务回滚时，清理未引用临时对象。
- G3 消费已提交交接后，独立负责解析任务执行、重试、解析终态和画像写入；G3 失败不回滚 G2 已提交的对象、简历和资料元数据。

## 失败处理与回滚边界

- 鉴权、归属或请求参数失败：事务不落库，临时对象立即清理。
- 类型、MIME、魔数或大小校验失败：返回统一业务错误，不保留对象。
- 幂等键重复且参数相同：返回原上传结果；参数不同：返回 409，不覆盖原资源。
- 对象存储失败或数据库事务回滚：返回脱敏错误；清理未引用对象，清理失败仅记录关联 ID、分类和耗时，不记录路径、原文或凭证。
- 上传和契约交接成功后，下游解析失败不回滚本模块已提交的资料资源，也不改变本模块上传验收结果；失败分类、解析终态和画像由文档解析模块负责。

## 阶段 3 固化方案

### 1. 设计依据与门禁状态

- 需求依据：`01-analysis/requirements.md`、`01-analysis/impact-analysis.md`。
- 外部能力依据：`02-validation/prevalidation.md`；本阶段复用已验证的 PostgreSQL/Repository、认证归属链和本地对象存储，不新增外部技术能力。
- 跨模块契约：`.harness/contracts/resume-parse-request-v1.yaml` 中的 `ResumeParseRequestV1@v1`。
- 契约状态：`locked`；联合门禁：`JCG-2026-020-021-RESUME-PARSE-V1`；`contract_hash`：`9AB937AE08E4A69C3D1D87C1968B8C17D7B6371984E236B1481C984F49EC9B18`。
- 参与方：CHG-020 为 producer，CHG-021 为 consumer；G2 负责持久化交接，G3 负责消费和解析执行。

契约文件是字段和跨模块语义的唯一权威来源。普通需求、方案和任务文档不得在该契约之外增加授权字段、幂等字段、路径、URL、对象键、正文或模型参数。

### 2. 数据模型与任务占位

本方案复用现有 `stored_file_objects`、`resumes`、`candidate_documents` 和 `async_task_runs`，不新增 handoff 表和数据库迁移。正式简历的 G2 事务写入集合如下：

| 数据对象 | 关键写入/复用规则 | G2 责任 |
| --- | --- | --- |
| `StoredFileObject` | 复用同摘要的 `ready` 对象；新对象只能在完成受控写入后由 Repository 标记为 `ready` | 创建/复用对象引用；不得返回 `storage_key` |
| `Resume` | 新建归属当前 `candidate_id` 的简历；同上传幂等键和同内容/名称重放既有资源 | 创建或复用正式简历 |
| 上传幂等关系 | 使用 `resumes(candidate_id, upload_idempotency_key)` 唯一约束；冲突请求返回 409 | 创建/读取/校验 |
| `AsyncTaskRun` | `task_type=resume_parse`、`resource_type=resume`、`resource_id=resume_id`、`task_version=v1`、`status=queued`、`celery_task_id=NULL` | 唯一创建/复用 queued 任务 |

任务幂等键固定为 `resume_parse:{resume_id}:v1`，并由既有 `async_task_runs` 唯一约束保护。同一 `resume_id + task_version` 不得创建第二条有效任务；G2 不负责 Dispatcher 投递和 Celery 消费。

### 3. Service/Repository 分层与外层事务

G2 采用“Service 编排、Repository 执行数据访问”的边界：

1. API 取得 `CurrentIdentity`，校验 multipart、文件类型、大小、内容特征和 `Idempotency-Key`，并将候选人身份传入 Service；客户端提交的 `candidate_id` 不作为可信来源。
2. Service 负责对象临时写入、业务顺序和统一结果映射，但不访问 ORM Session、SQL 或本地正式文件路径。
3. `CandidatePreparationRepository` 提供加入既有 Session/事务的简历资源创建或复用能力；不得在该方法内部独立 `begin/commit`。
4. `AsyncTaskRepository` 提供加入同一 Session/事务的 `create_or_get_queued_resume_task` 能力，按固定任务类型、资源 ID和版本执行归属、资源状态、唯一性和复用校验。
5. Service 在同一个外层数据库事务中依次协调 `StoredFileObject`、`Resume`、上传幂等关系和 `AsyncTaskRun`；只有事务提交成功后 API 才返回 `201 / UPLOAD_ACCEPTED`。

当前 `CandidatePreparationRepository.create_resume()` 自行开启事务的实现不能直接作为本方案实现依据；阶段 5 必须先将事务边界收归 G2 Service/Repository 协调层，再实现 queued 任务创建/复用。

### 4. 正式简历上传事务序列

```text
CurrentIdentity.candidate_id
  -> API 输入/文件安全校验
  -> 临时对象写入、摘要与 MIME 检测
  -> Repository 校验上传幂等键
  -> 外层 PostgreSQL 事务开始
       -> 锁定/复用 ready StoredFileObject
       -> 校验 candidate_id -> Resume 归属
       -> 创建/复用 Resume 与上传幂等关系
       -> 校验对象 ready
       -> 创建/复用 AsyncTaskRun(status=queued)
     -> 提交事务
  -> 返回 201 / UPLOAD_ACCEPTED / processing
  -> G3 后续消费 queued 任务
```

事务内任一校验、唯一约束或写入失败，整体回滚；本次暂存对象若未被任何业务资源引用则立即清理，清理失败只进入受控清理机制。G3 后续失败只更新解析侧终态，不回滚已提交的 G2 资源。

### 5. 幂等与并发决策

| 场景 | 方案结果 |
| --- | --- |
| 同一候选人、同一上传幂等键、同一内容摘要和名称 | 返回原 `resume_id`、`201 / UPLOAD_ACCEPTED` 和 `processing`；复用原 queued 任务 |
| 同一候选人、同一上传幂等键但内容或名称不同 | 返回 `409 / IDEMPOTENCY_KEY_CONFLICT`；不覆盖原资源、不创建任务 |
| 同一内容摘要被不同候选人上传 | 复用底层 `StoredFileObject`，分别创建候选人自有 `Resume` 和唯一任务 |
| 同一 `resume_id + v1` 并发创建任务 | 依赖唯一约束和 Repository 冲突后读取，最终只保留一个有效 queued 任务 |
| 对象不存在、状态非 `ready` 或归属不符 | 安全失败；不创建有效任务，不泄露对象定位信息 |

并发处理不得使用客户端生成的任务 ID、随机幂等字段或契约扩展字段解决；任务唯一性以数据库约束和事务内 Repository 复用为准。

### 6. API、状态与错误映射

正式简历接口固定返回：

```json
{
  "code": "UPLOAD_ACCEPTED",
  "msg": "上传已受理，正在解析简历",
  "data": {
    "resume_id": "<uuid>",
    "parse_status": "processing"
  }
}
```

该响应只表示 G2 资源和 queued 任务交接已可靠提交，不表示 MinerU、Qwen 或画像生成成功。状态责任为：

```text
G2: 资源事务提交 -> resumes.processing + async_task_runs.queued
G3: queued -> running -> succeeded / failed
```

G2 只映射认证、输入、归属、对象、幂等和事务错误；不生成 G3 的解析失败码，不读取 G3 任务终态，不调用 G3 内部 Service。所有 API 遵循 `{code,msg,data}`，错误响应不得包含路径、对象键、正文、堆栈或供应商原始响应。

### 7. 阶段 3 通过后的实现约束

- 本方案不授权代码、迁移执行或测试实现；双方阶段 3 已通过，阶段 4 可按独立任务拆分门禁启动，阶段 5 仍未授权。
- 阶段 4 只能拆分本方案已固化的 G2 事务协调、Repository 创建/复用、API 受理响应和失败清理任务，不得再次决定任务创建方或契约字段。
- 若阶段 4/5 发现现有唯一约束不足、对象状态无法可靠验证或事务边界需要增加表/字段，必须停止并按阶段 3 回退规则重新裁决。

## 历史设计（废止）

本节只保留历史决策痕迹，不构成当前方案。曾经将 G2 直接调用解析任务、在 G2 内定义解析状态或把 G3 执行结果作为 G2 成功条件的表述均已废止。当前以本文前述 G2/G3 边界、固定交接记录/排队占位、事务、幂等和失败回滚规则为唯一方案依据。
