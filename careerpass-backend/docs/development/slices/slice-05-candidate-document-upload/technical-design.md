# Slice：S-05 求职者资料上传技术设计

> 业务目标、规则、范围和验收标准以同目录 `slice-spec.md` 为准；本文锁定 API、数据、事务、前端交接和验证边界。

## 1. 依赖与交付关联

| 内容 | 约定 |
| --- | --- |
| 身份 | S-01 `CurrentIdentity → Candidate` |
| 资源 | `CandidateDocument → StoredFileObject` |
| Integration Contract | [`IC-S05-CANDIDATE-DOCUMENT-UPLOAD@0.1`](../../../../../docs/integration/slices/slice-05-candidate-document-upload/integration-contract.md) |
| Integration Scenario | [`IS-S05-01`](../../../../../docs/integration/slices/slice-05-candidate-document-upload/integration-scenario.md) |
| 异步任务 | 无 |
| 后端状态 | `backend_ready`；代码、隔离 PostgreSQL、对象存储和候选人隔离测试已验证 |

## 2. API 与结果契约

### `POST /api/v1/candidate_documents`

- 认证：已登录 Candidate；服务端复核 `CurrentIdentity → Candidate`。
- 请求：multipart `files`，至少一份文件；不接收 `candidate_document_type`。
- 支持：`.pdf`、`.md`、`.jpg`、`.png`；单文件不超过 10 MB。
- 响应：统一 `{code, msg, data}`，`data.results` 按输入顺序逐文件返回。
- 单文件结果：`created`、`duplicate` 或 `failed`。
- 成功资料元数据：资料 ID、原始文件名、文件格式、上传状态 `success`、上传时间。
- 失败结果：原始文件名、`failed` 状态、安全失败分类；资料 ID和上传时间为空。
- `created` 和 `duplicate` 均映射为前端成功结果；`failed` 由页面转换为一次性 error Snackbar/Toast，失败结果不保留为持久页面状态。
- 不返回原文件、文件正文、对象存储键、内部路径或原始异常。

### `GET /api/v1/candidate_documents`

- 仅返回当前 Candidate 的正式成功资料。
- 支持现有分页参数，不再提供用户资料分类过滤。
- 列表字段：资料 ID、名称、文件格式、上传状态 `success`、创建/上传时间。
- 不返回版本、正文、下载地址、对象键或其他内部定位。

## 3. 数据、事务与幂等

- 不新增表或迁移；现有 `CandidateDocument.document_type` 固定保存 `other`，不进入公开 Contract。
- `StoredFileObject.content_sha256` 继续作为文件内容摘要和对象复用依据。
- 每个文件独立执行：对象存储写入、文件对象复用/创建、CandidateDocument 创建在同一业务事务边界内完成。
- 失败文件回滚自身数据库写入并清理未引用临时对象，不影响同批次其他文件。
- 同一 Candidate + 相同内容摘要命中既有资料时返回 `duplicate`，不创建 CandidateDocument。
- 可选 `Idempotency-Key` 按文件内容派生稳定请求键，重放同一批次不会产生重复资源；内容幂等规则优先于请求键。
- 当前不验收并发重复上传竞态；后续如纳入，需回退 Slice Design 增加数据库约束或锁定策略。

## 4. 状态与分层实现

```text
前端选择文件
  → 临时 ready
  → API 逐文件校验
  → 对象存储与数据库事务
  → success / duplicate
  → 失败时 failed（仅前端结果，不持久化）
```

- `ready` 和 `failed` 是前端上传结果投影，不增加 CandidateDocument 状态字段。
- 成功资料由 CandidateDocument 的存在表达；列表统一返回 `success`。
- Controller 负责 multipart、身份上下文和统一响应。
- Service 负责逐文件校验、对象存储编排、失败清理和结果映射。
- Repository 负责 Candidate 归属、内容摘要重复查询、文件对象和资料持久化。
- Object Storage 只负责受控写入和临时对象清理。

## 5. 失败与安全

| 场景 | 处理 |
| --- | --- |
| 空文件 | 当前文件 `failed`，不创建业务记录 |
| 不支持格式或格式签名不匹配 | 当前文件 `failed`，不创建业务记录 |
| 超过 10 MB | 当前文件 `failed`，不创建业务记录 |
| 对象存储失败 | 当前文件 `failed`，清理临时对象，不影响其他文件 |
| 数据库事务失败 | 当前文件 `failed`，回滚当前文件，不影响其他文件 |
| 其他 Candidate 访问 | 拒绝，不泄露资源存在性 |
| 重复上传 | 返回既有资料为幂等成功 |

响应、日志和追踪不得包含文件正文、对象键、路径、原始异常、凭证或其他敏感内容；只记录必要的关联 ID、阶段、结果和脱敏失败分类。

## 6. Readiness Check

| 项目 | 状态 |
| --- | --- |
| 故障案例匹配 | 未匹配新的故障案例；本 Slice 不依赖异步基础设施 |
| PostgreSQL / migration | 通过；统一预检 `status=ready`，S05 API 集成测试通过 |
| 受控对象存储 | 通过；本地适配器、失败清理和真实对象存储写入验证通过 |
| S01 Candidate 身份 | 通过；真实登录、当前 Candidate 归属和跨 Candidate 隔离验证通过 |
| Redis / Celery / Worker | 不适用 |

## 7. 验证计划

- Service 单元：四种合法格式、大小边界、非法格式、空文件、逐文件失败和临时对象清理。
- Repository/数据库集成：Candidate 归属、内容摘要幂等、列表安全字段和失败不落库。
- API 集成：批量部分成功、重复上传、分页、未登录、其他 Candidate 和统一响应。
- 前端单元：`ready → success/failed`、格式白名单、无版本字段、失败 Snackbar/Toast、无重试入口和 Mock/HTTP 映射。
- 前端场景：真实登录、批量选择合法与非法文件、成功提示、失败反馈和列表更新。

当前验证证据：后端全量单元测试 `184 passed`；S05 定向单元测试 `23 passed`；真实隔离集成测试中 S05 相关测试 `2 passed`；前端构建、Lint、Prettier 检查和 `36` 项测试均通过；开发者已完成真实前端联调和失败提示整改复测，结果记录在 `IS-S05-01`。

## 8. 关闭条件

- Slice Spec、Technical Design、Contract、Scenario 与代码一致；
- 后端定向测试和真实 PostgreSQL/对象存储验证通过；
- 前端 Mock、真实 HTTP Repository 和页面结果一致；
- 开发者完成 `IS-S05-01` 最小演示并审阅问题整改；
- `IS-S05-01` 已由开发者验收为 `integration_delivered`，S-05 跨端交付完成。
