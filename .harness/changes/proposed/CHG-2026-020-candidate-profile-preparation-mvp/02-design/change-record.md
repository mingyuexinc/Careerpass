# CHG-020 阶段 3 方案设计变更记录

## 变更包与依据

- 变更包：`CHG-2026-020-candidate-profile-preparation-mvp`
- 阶段：3. 方案设计
- 权威方案：`02-design/design.md`
- 需求：`01-analysis/requirements.md`
- 影响分析：`01-analysis/impact-analysis.md`
- 阶段 2 预验证：`02-validation/prevalidation.md`
- 跨包契约：`.harness/contracts/resume-parse-request-v1.yaml`
- 联合评审：`.harness/contracts/JCG-2026-020-021-RESUME-PARSE-V1-joint-review.md`

## 本阶段固化的设计决策

| 决策项 | 当前方案 | 设计依据 |
| --- | --- | --- |
| 生产者责任 | G2 是 `ResumeParseRequestV1@v1` producer，并在资源事务中创建/复用 queued `AsyncTaskRun` | 已锁定契约、需求分析 |
| 消费者责任 | G3 只消费已有 queued 任务，不创建第二个任务，不调用 G2 内部实现 | 已锁定契约、CHG-021 联合评审 |
| 事务边界 | `StoredFileObject`、`Resume`、上传幂等关系和 queued 任务由同一外层 PostgreSQL 事务提交 | 阶段 2 PostgreSQL/Repository 证据、异步任务技术方案 |
| Repository 边界 | Service 编排；所有数据访问经 Repository；Repository 不独立提交内部事务 | 数据访问红线、现有事务缺口 |
| 任务模型 | 复用 `async_task_runs`，固定 `resume_parse:{resume_id}:v1`，不新增 handoff 表 | 数据模型、异步任务技术方案 |
| API 受理语义 | 返回 `201 / UPLOAD_ACCEPTED`、`resume_id`、`parse_status=processing`；不表示解析成功 | 接口协议、需求分析 |
| 对象状态 | 只有 `StoredFileObject.status=ready` 且归属校验通过才可建档并创建/复用任务 | 对象存储技术方案、阶段 2 验证计划 |
| 幂等与失败 | 上传幂等和任务幂等分别由资源唯一约束、任务唯一约束和 Repository 复用保证；失败不留下悬挂任务 | 数据模型、阶段 2 预验证 |
| 外部能力 | 不新增或重新选择 PostgreSQL、对象存储、Redis、Celery、MinerU、Qwen 等能力 | 阶段 2 裁决 |

## 影响与回滚

- 本阶段不执行代码、数据库迁移或接口变更；阶段 4/5 仍未授权。
- 方案复用现有数据模型，不新增 handoff 表；如果后续实现证明现有唯一约束或对象状态不足，最低回退到阶段 3，必要时所有参与包共同回退。
- 契约已锁定，文件哈希为 `9AB937AE08E4A69C3D1D87C1968B8C17D7B6371984E236B1481C984F49EC9B18`。契约语义不得原地修改。
- 既有实现和测试记录保留为历史证据，不能作为本次新边界的阶段 5/6 通过证据。

## 阶段 3 状态

方案文档和变更记录已形成，跨包契约已由双方开发者联合锁定。开发者已于 2026-08-02 完成本包方案人工复核，CHG-020 阶段 3 已标记为 `passed`；阶段 4 尚未启动，后续按双方阶段 3 均通过后的阶段 4 门禁推进。
