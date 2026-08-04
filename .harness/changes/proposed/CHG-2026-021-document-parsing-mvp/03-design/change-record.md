# 阶段 3 方案设计变更记录

## 变更包

- 变更：`CHG-2026-021-document-parsing-mvp`
- 模块：简历解析与候选人画像分支
- 阶段：3. 方案设计
- 设计文档：`03-design/design.md`

## 设计依据

- `01-analysis/requirements.md`
- `01-analysis/impact-analysis.md`
- `02-validation/prevalidation.md`
- `02-validation/worker-prevalidation.md`
- `.harness/wiki/03-contracts/Interface protocol.md`
- `.harness/wiki/03-contracts/Data model.md`
- `.harness/wiki/04-technical-solutions/Async task technical design.md`
- `.harness/wiki/04-technical-solutions/Object storage technical design.md`
- `.harness/wiki/04-technical-solutions/Resume parsing technical design.md`

## 修订前置门禁状态

- 阶段 1：`passed`，需求已明确 CHG-020 producer、CHG-021 consumer 及 G2/G3 责任边界。
- 阶段 2：`passed`，既有 PostgreSQL/Repository、对象存储、Redis、Dispatcher、Celery Worker、MinerU MCP 和 Qwen Plus 能力均按既有证据复用；Worker 真实 Compose 复验已覆盖启动、租约、成功、超时、重复投递和中断接管。
- 跨包契约：`ResumeParseRequestV1@v1` 已 `locked`，双方开发者已批准，`contract_hash` 为 `9AB937AE08E4A69C3D1D87C1968B8C17D7B6371984E236B1481C984F49EC9B18`。

## 本阶段固化的设计决策

| 决策 | 方案 | 依据 |
| --- | --- | --- |
| 触发边界 | CHG-020 在资源事务中创建/复用 queued `AsyncTaskRun` 并交接 `ResumeParseRequestV1@v1`；G3 只消费既有任务，Agent 不作为上传后解析决策者 | 需求裁决、跨模块责任边界、统一契约注册表 |
| 执行方式 | Dispatcher + Redis Broker + Celery Worker 异步执行，PostgreSQL 为任务权威状态 | MinerU 为外部依赖；阶段 2真实 Worker/重投递证据 |
| 输入定位 | 仅传 `candidate_id`、`resume_id`、`task_version="v1"`；不传受控读取授权、幂等键、路径、URL、对象键、正文或模型参数 | 统一契约注册表、对象存储和安全红线 |
| 解析链路 | 受控对象读取 → MinerU 文本提取 → Qwen JSON Schema → Pydantic/业务校验 → 原子画像/终态 | 简历解析技术方案、预验证记录 |
| 中间结果 | Markdown 只在内存中存在，不写入数据库或 API | MVP 范围和数据模型 |
| 成功条件 | `target_job_titles` 至少一个非空值，并与画像、简历、任务终态同事务提交 | 数据模型和业务规则 |
| 失败策略 | 临时依赖故障有限重试；确定性输入/Schema 故障不重试；失败码使用枚举 | 异步任务和简历解析技术方案 |
| 用户体验 | 上传响应仅表示已受理；前端自动查询列表状态，不要求手动刷新 | 接口协议与需求文档 |
| 发布边界 | 不新增迁移；契约联合锁定、双方阶段 3 通过后才能进入阶段 4；代码实现仍未授权 | 需求影响分析和门禁规则 |

## 本次方案修订内容

1. 清除阶段 1/2 尚待复核及阶段 2 Worker 阻塞的过渡性表述，以当前 `passed` 台账和真实复验记录为准。
2. 固化 G3 consumer 边界：G3 只接收内部 `task_run_id`，消费 G2 已创建/复用的 queued `AsyncTaskRun`，不创建第二个任务，不调用 G2 内部 Service/Repository 实现。
3. 固化任务消费前的 Repository 复核：任务类型/资源类型、`candidate_id`、`resume_id`、`task_version=v1`、候选人归属、简历 `processing`、对象 `ready` 和当前执行租约必须一致。
4. 固化 G3 的解析成功/失败事务、令牌条件围栏、重复投递/迟到令牌无副作用和 G2/G3 失败隔离。
5. 明确阶段 2 的外部能力证据只支持方案选型和运行拓扑复用，不替代阶段 6/8 的 G2→G3 业务联调及完整画像验收。

## 影响与回退

本阶段未改变已批准的 MVP 范围、接口协议、数据模型、状态机或外部依赖。若评审后新增字段、替换第三方依赖、改变失败策略或改变跨模块授权边界，必须按开发流程规范回退到对应阶段重新通过门禁。

## 阶段 3 结论

本记录与 `03-design/design.md` 已按当前需求、阶段 2 `passed` 证据和锁定契约完成方案修订。开发者已于 2026-08-02 完成人工方案复核，CHG-021 阶段 3 已标记为 `passed`；阶段 4 尚未启动，阶段 5 编码仍未授权。
