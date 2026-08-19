# Slice：岗位 JD 上传技术设计

> 业务规格以 [`slice-spec.md`](slice-spec.md) 为准；本文件只记录 API、数据、异步交接、实现边界和验证要求。

## 1. 依赖与事实源

| 内容 | 文档 |
| --- | --- |
| 跨前后端业务事实 | [`business-baseline.md`](../../../../../docs/business/business-baseline.md) |
| 领域对象与状态 | [`domain-model.md`](../../../domain/domain-model.md) |
| 数据库结构 | [`database-design.md`](../../../data/database-design.md) |
| 跨 Slice 规则 | [`business-rules.md`](../../../product/business-rules.md) |
| 异步任务架构 | [`async-task-architecture.md`](../../../architecture/async-task-architecture.md) |
| 跨端 Integration Contract | [`IC-S02-JD-UPLOAD`](../../../../../docs/integration/slices/slice-02-jd-upload/integration-contract.md) |
| 跨端 Integration Scenario | [`IS-S02-01`](../../../../../docs/integration/slices/slice-02-jd-upload/integration-scenario.md) |

当前 S-02 的业务裁决已同步至业务基线。API、Job 迁移和 S-03 任务技术字段属于 Coding Agent 的实现决策；跨端上传结果、自动上传交互和 `.md` 格式限制已由 `IC-S02-JD-UPLOAD@0.3` 锁定。S-02 页面只展示“上传成功”或“上传失败”，不展示“解析中”、岗位摘要或解析结果；S-02 只负责上传，不负责岗位读取。HR 已上传岗位的持久化读取和跨角色恢复由 S-09 的独立 HR Job 查询边界负责，不改变 S-02 上传接口。解析失败 Job 再次上传时，未删除 Job 由 S-03 复用并重建解析任务，已删除 Job 不复用。

## 2. 接口设计边界

S-02 已锁定 `POST /api/v1/jobs`；以下 API 语义和实现字段已落实：

| 项目 | 约定 |
| --- | --- |
| 输入 | 一个已认证 HR 通过 multipart 字段 `files` 提交一份或多份 `.md` JD 文件 |
| 处理粒度 | 逐文件处理，不以整个批次作为一个 Job |
| 成功结果 | HTTP 200，返回 `data.results` 逐文件结果 |
| 重复结果 | 返回已有未删除 Job，作为幂等成功 |
| 失败结果 | 逐文件返回安全失败结果；当前 Demo 不验收失败展示/恢复 |
| 统一响应 | `{code, msg, data}`；结果为 `created`、`duplicate` 或 `failed` |
| 敏感边界 | 不返回正文、路径、对象键、原始异常或凭证 |

建议的逻辑结果值：`created`、`duplicate`、`failed`。具体外部字段不在本文件中提前发明。

## 3. 数据设计与事务

### 3.1 资源关系

```text
HrProfile 1 ── N Job
Job 1 ── 1 StoredFileObject
Job 1 ── 0..1 ParsedJobDescriptionSnapshot（由 S-03 创建）
Job 1 ── 1 有效 JD 解析任务（由 S-02 创建/复用 queued 交接记录）
```

`JD 输入资源`不单独建表，由 `Job` 与 `StoredFileObject` 的关联表达。

### 3.2 Job 最小字段

| 字段 | 约束方向 | 用途 |
| --- | --- | --- |
| `id` | UUID 主键 | Job 标识 |
| `hr_profile_id` | 非空外键 | 资源归属 |
| `stored_file_object_id` | 非空外键 | JD 文件关联 |
| `file_name` | 可空字符串 | 上传时的原始文件名；历史 Job 为空时由 HR 查询使用安全回退文案 |
| `created_at` | 非空时间 | 创建记录 |

Job 不保存岗位结构化展示字段、解析状态或 JD 版本号。删除状态的具体字段由 S-11 设计。

### 3.3 重复判断

| 条件 | 处理 |
| --- | --- |
| 当前 HR、相同内容摘要、存在未删除 Job | 返回已有 Job |
| 当前 HR、相同内容摘要、仅存在已删除 Job | 不复用，创建新 Job |
| 内容摘要不同 | 创建新 Job |
| 解析中 Job | 返回已有 Job，不重复创建任务 |
| 解析失败 Job | 未删除 Job 由 S-03 复用并重建解析任务；已删除 Job 不复用，重新上传创建新 Job |

不同 HR 的内容复用和并发重复上传不属于当前 Demo 验收。

### 3.4 事务边界

新文件的以下记录必须在同一 PostgreSQL 事务内提交：

```text
StoredFileObject 元数据
+ Job
+ Job 与文件关联
+ queued S-03 AsyncTaskRun 交接记录
```

事务失败不得留下可供 S-03 消费的半成品 Job；未引用临时对象按对象存储清理规则处理。批量文件逐项处理，单项失败不回滚已成功项。

## 4. S-02 → S-03 异步交接

| 项目 | 约定 | 状态 |
| --- | --- | --- |
| Producer | S-02 | 已确认 |
| Consumer | S-03 | 已确认 |
| 交接标识 | `job_id` | 已确认 |
| 任务记录 | 上传事务内创建/复用 `queued` `AsyncTaskRun` | 已确认 |
| 任务幂等 | 活动任务按 `job_jd_parse:{job_id}:v1:{generation}` 复用；失败任务递增 `generation` 重建，任务类型 `job_jd_parse`，资源类型 `job` | 已落实 |
| 任务执行 | 事务提交后由 Dispatcher/Worker 投递和执行 | 已确认 |
| 直接调用 | S-02 不调用 S-03 Service、Dispatcher 或 Worker | 已确认 |
| 解析终态 | S-03 持有并更新 | 已确认 |
| 解析失败后重传 | S-03 定义 | 未删除 Job 复用并重建任务；已删除 Job 创建新 Job |

任务输入只包含经过服务端校验的资源标识，不包含路径、URL、对象键、文件正文、模型参数或自由指令。

## 5. 分层实现边界

| 层 | 职责 |
| --- | --- |
| Controller | 解析批量输入、身份上下文和统一响应 |
| Service | 编排逐文件上传、重复判断、Job 创建和事务边界 |
| Repository | 查询/创建 Job、文件对象和任务，执行 HR 归属与重复判断 |
| Object Storage | 受控写入和清理文件对象 |
| Dispatcher/Worker | 事务提交后投递和执行 S-03 任务 |

Service 不直接访问 ORM Session 或编写 SQL；所有 Job 和文件资源访问必须经过 Repository 归属校验。

## 6. 状态与删除边界

| 状态/事实 | 拥有者 | S-02 行为 |
| --- | --- | --- |
| Job 已创建 | S-02 | 创建或复用 |
| 解析任务 `queued` | S-02/异步基础设施 | 在上传事务内创建或复用 |
| 解析中/成功/失败 | S-03 | S-02 不写入终态 |
| 匹配是否已发起 | S-08 | S-02 不判断业务结果 |
| Job 删除 | S-11 | S-02 不执行；已删除 Job 不参与重复判断 |

## 7. 失败与安全

| 场景 | 处理 |
| --- | --- |
| 文件输入不合规 | 该文件失败，不创建可用 Job；当前 Demo 不验收失败恢复 |
| 归属不符 | 拒绝访问，不泄露资源存在性 |
| 对象存储或事务失败 | 回滚 Job/任务交接，清理未引用临时对象 |
| 批量单项失败 | 保留其他成功项结果 |
| 顺序重复上传 | 返回已有未删除 Job，作为幂等成功 |
| 解析失败后重传 | 未删除 Job 复用并重建任务；已删除 Job 不复用，创建新 Job |

日志和追踪仅记录脱敏关联 ID、阶段、状态、失败分类、耗时和重试次数等最小诊断信息。

## 8. Readiness Check 前置条件

| 项目 | 当前状态 |
| --- | --- |
| S-02 业务边界 | 已裁决 |
| Job 最小数据关系 | 已形成，由 Coding Agent 落实迁移 |
| 批量逐文件处理 | 已裁决 |
| 顺序重复上传 | 已裁决 |
| 删除 Job 后重传 | 已裁决 |
| 解析中 Job 重传 | 已裁决 |
| 解析失败 Job 重传 | 已由 S-03 契约确认，不阻塞 S-02 |
| S-03 任务类型、资源类型、版本和失败契约 | Coding Agent 自主落实 |
| 业务基线 `BF-SCOPE-007/008/009` | 已同步为 `confirmed` |
| API 字段和错误码 | 已落实为 `POST /api/v1/jobs` 及逐文件结果 |
| Job Alembic migration | 已实现 `20260813_0006` |

## 9. 验证计划

- 批量上传逐文件结果和部分成功；
- 内容不同创建独立 Job；
- 同一 HR 顺序重复上传返回已有 Job；
- 解析中重复上传不创建新 Job 或新任务；
- 已删除 Job 不参与去重，重传创建新 Job；
- 新 Job、文件关联和 queued 任务交接原子提交；
- S-02 不直接调用 S-03 Service、Dispatcher 或 Worker；
- 资源归属和敏感信息边界；
- 真实 PostgreSQL、对象存储和任务交接验证；
- S-03 真实解析和解析失败后重传由 S-03 实现；S-02 仅验证上传资源、Job 归属和任务交接不被破坏。

## 10. 关闭条件

- API、Job 迁移和 S-03 任务技术字段完成并通过 Readiness Check；
- 业务基线、领域模型、数据库设计和业务规则与本设计一致；
- 后端接口、数据库事务、批量结果、顺序幂等和跨角色归属测试通过；
- Integration Contract 已锁定，前端 S-02 专用 HTTP Repository、真实 API 和页面状态映射一致；
- 前端自动化测试和后端 S-02 定向测试已通过；
- Integration Scenario 已完成业务事实变更后的真实链路执行，问题整改并完成回归；
- 前端真实接入能够按文件顺序区分“上传成功”和“上传失败”，但不消费或展示 S-03 解析状态；
- 不产生真实外部招聘副作用。
