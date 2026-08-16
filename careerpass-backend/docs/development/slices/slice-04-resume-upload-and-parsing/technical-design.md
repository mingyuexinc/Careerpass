# Slice：S-04 简历上传与解析技术设计

> 业务事实以 `slice-spec.md` 和业务基线为准；本文件锁定 API、数据、任务、前端交接和验证边界。

## 1. 依赖与交付边界

| 内容 | 约定 |
| --- | --- |
| 身份 | S-01 `CurrentIdentity → Candidate` |
| 上传资源 | Candidate-owned `Resume → StoredFileObject` |
| 任务 | `resume_parse`，PostgreSQL `AsyncTaskRun` 为权威状态 |
| 解析链路 | 受控文本 PDF → 原生嵌入文本提取（无文本时 MinerU 回退）→ Qwen 结构化画像 → Pydantic/业务校验 |
| 前端 | 真实 HTTP 上传和 Resume 状态查询；不消费画像响应 |
| 下游 | S-07 消费已校验画像及匹配资格并在启动时绑定当前简历；S-06 不依赖 S-04，不由 S-04 创建目标或启动 Agent |

## 2. API 边界

### `POST /api/v1/resumes`

- 认证：Candidate；服务端复核 Candidate 归属；
- 输入：multipart `file`，单个 PDF；
- 可选 `name` 和 `Idempotency-Key` 继续作为上传元数据和请求幂等辅助字段；内容摘要是业务去重依据；
- 响应：统一 `{code,msg,data}`，只返回 `resume_id`、当前 `parse_status` 和必要的处理结果元数据；不返回画像；
- 新 PDF：创建 Resume 和一个 queued `resume_parse` 任务；
- 相同 PDF：返回已有 Resume 当前状态，不创建新 Resume、版本或任务。

### `GET /api/v1/resumes`

- 仅返回当前 Candidate 的 Resume 列表和解析状态；
- 用于前端刷新/轮询处理状态；
- 不返回文件路径、对象键、简历正文、画像字段或模型响应。

### `GET /api/v1/resumes/{resume_id}/profile`

- 仅供 Candidate-owned 后端读取和后续 Slice 交接；
- 不由本次简历上传页调用或展示；
- 返回前必须复核 `Candidate → Resume → CandidateProfile` 归属和成功状态。

## 3. 数据与状态

- `Resume` 保持 Candidate 1:N；
- `StoredFileObject.content_sha256` 作为文件内容唯一摘要；
- Repository 查询 `candidate_id + content_sha256`，命中后复用 Resume；
- `AsyncTaskRun.idempotency_key` 使用 Resume 标识和任务版本，确保一个 Resume 只有一个有效解析任务；
- `CandidateProfile` 与 Resume 1:1；
- 画像新增姓名、手机号、邮箱及匹配资格所需的可选/必选信息；
- `matching_ready/not_ready` 作为画像业务判定，必须由后端校验产生，不由客户端提交。

## 4. 异步事务

新 PDF 的以下记录在同一 PostgreSQL 事务内提交：

```text
StoredFileObject ready
+ Resume
+ queued AsyncTaskRun
```

重复 PDF 只返回既有资源；临时上传对象在事务未使用或命中已有内容时清理。

Worker 只能接收 `task_run_id`，根据 Repository 复核 Candidate-owned Resume 和 ready 文件对象；成功时画像、Resume 终态和 AsyncTaskRun 终态原子提交；失败时不创建画像。

## 5. 解析 Schema 与校验

画像输入必须经 `ResumeProfileExtractionV1` 校验后才能入库。必需业务校验为：

- `full_name` 非空；
- `phone` 或 `email` 至少一个非空；
- `education` 有效；
- `work_experience_summary` 或 `project_experience_summary` 至少一项有效。

其它字段均可为空或为空数组。Schema 校验成功后再执行业务资格判定；业务资格不满足时仍可写入成功画像，但判定为 `matching_not_ready`。

文本型 PDF 的姓名、联系方式和教育从原生文本确定性提取；Qwen 只提取需要语义关联的工作/项目经历。公司、岗位和项目名称必须能由原生文本主源支持，同一公司值不得超过主源出现次数；缺失或串位时只对受影响的经历字段使用小 Schema 纠偏一次，连续失败形成 `schema_validation_failed`。工作经历标记为 `work/internship`；年月统一标准化为 `YYYY-MM/present`，`years_of_experience` 合并非实习有效年月区间后按 `BF-RULE-019` 生成 `unknown`、`x个月` 或 `x年`。

## 6. 前端状态映射

| 后端状态 | 前端展示 |
| --- | --- |
| 上传请求成功 | 上传成功/解析中 |
| `processing` | 解析中 |
| `succeeded` | 解析成功 |
| `failed` | 解析失败 |

前端不显示 `matching_ready/not_ready`、画像字段、联系方式、教育内容或完整简历文本。

## 7. 能力验证分层

- Capability Acceptance：固定 PDF 直接执行核心解析和画像校验，不依赖登录、数据库、Redis、Celery、上传 API 或前端；
- Slice Integration：真实上传、对象存储、任务创建、持久化和状态交接；
- Infrastructure：Dispatcher、Redis、Celery、租约、重试和迟到 Worker；
- E2E：真实登录、上传 PDF 和前端状态展示。

Acceptance Artifact 至少包含 `report.md` 和 `actual.json`；不写入完整简历原文、内部路径、模型原始响应或不必要敏感信息。

## 8. 外部解析边界与时限

- 文本型 PDF 优先使用本地嵌入文本作为事实主源；本地无文本时才调用 MinerU 回退，MinerU 结构化错误不得继续交给 Qwen；
- MinerU Bridge 只继承运行、代理和证书所需环境，并对已验证的结果 CDN 使用受控直连；
- Qwen 经严格小 Schema 返回工作/项目列表；中文年月、斜杠年月和“至今”由代码标准化；
- 经历漏抽、缺少主源支持或公司发生无依据重复时，只对经历字段纠偏一次；耗尽后形成 `schema_validation_failed`；
- Worker 硬时限、软时限和执行租约依次为 150、120 和 180 秒；Capability Acceptance 使用 120 秒外部调用预算。

## 9. 关闭记录

- 固定 PDF Capability Acceptance 已由开发者运行并裁定通过，结果为 `parse_succeeded + matching_ready`；必需字段、工作年限派生和两段正式工作公司区分断言均通过。
- 真实解析交付链路的代码、任务状态、画像持久化和外部解析调用验证已完成；前端只消费上传和解析状态，不消费画像或匹配资格详情。
- 当前仅保留成功验收产物：`careerpass-backend/tests/acceptance/s04_resume_parse/delivery-acceptance-results/20260815T155611Z-fc83327a`。此前最终判定失败的产物已按开发者裁定删除。
- S-04 关闭状态为 `integration_delivered`；后续 S-07 接收已校验画像和匹配资格，S-06 不依赖 S-04；不扩大本 Slice 范围。
