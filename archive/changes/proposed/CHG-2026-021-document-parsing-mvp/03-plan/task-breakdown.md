# 简历解析与候选人画像阶段 4 任务拆分（已完成）

> 本文件是 CHG-021 阶段 4 的正式任务拆分交付物。`ResumeParseRequestV1@v1` 已锁定并登记 `contract_hash`、双方开发者批准；CHG-020 与 CHG-021 阶段 3 均已通过。本文件只授权阶段 5 执行下列已裁定任务，不重新定义契约、范围、数据模型、状态机或跨包责任。

## 当前跨包门禁

| 项目 | 当前要求 | 状态 |
| --- | --- | --- |
| 唯一契约 | `.harness/contracts/resume-parse-request-v1.yaml`，仅 `candidate_id`、`resume_id`、`task_version="v1"`，`extra="forbid"` | `locked` |
| 生产者 | CHG-020：在同一 PostgreSQL 事务中创建/复用 `AsyncTaskRun(status=queued)` | 已批准并固化 |
| 消费者 | CHG-021：只消费已有 queued 任务，不创建第二个任务，不调用 G2 内部 Service | 已批准并固化 |
| 联合门禁 | `JCG-2026-020-021-RESUME-PARSE-V1`；已登记哈希和双方批准 | 已完成 |
| 阶段 4 | 两个开发包阶段 3 通过、契约 locked 且哈希一致后才可开始 | 已满足并完成拆分 |

## 阶段 4 必填门禁表

### 参与开发包门禁

| 参与开发包 | 角色 | 所需阶段 | 实际状态 | 证据 | 批准人 | 未满足时处理 |
| --- | --- | --- | --- | --- | --- | --- |
| `.harness/changes/proposed/CHG-2026-020-candidate-profile-preparation-mvp` | producer | 阶段 3 | `passed` | `00-governance/stage-gates.yaml` | developer | 不得进入跨包实现；回退到受影响阶段 |
| `.harness/changes/proposed/CHG-2026-021-document-parsing-mvp` | consumer | 阶段 3 | `passed` | `00-governance/stage-gates.yaml` | developer | 不得进入阶段 4/5；补齐方案门禁 |

### 契约锁定表

| 契约 ID/版本 | 注册表 | 状态/哈希 | 生产者 | 消费者 | 联合批准证据 | 本任务使用方式 |
| --- | --- | --- | --- | --- | --- | --- |
| `ResumeParseRequestV1@v1` | `.harness/contracts/resume-parse-request-v1.yaml` | `locked` / `9AB937AE08E4A69C3D1D87C1968B8C17D7B6371984E236B1481C984F49EC9B18` | CHG-020 | CHG-021 | `.harness/contracts/JCG-2026-020-021-RESUME-PARSE-V1-joint-review.md` | G3 只消费 G2 已创建/复用的 queued 任务，不创建第二个任务 |

### 未决事项检查

以下事项均已在阶段 1–3 完成裁决，本阶段 4 不再新增决定：字段白名单、生产者/消费者、触发语义、任务创建方、事务边界、幂等键、资源归属、状态拥有者、失败分类、重试策略、授权链和安全脱敏边界均无未决项。若阶段 5 实现或阶段 6 验证发现上述事项发生变化，必须停止当前任务，并按跨包回退规则至少回退到阶段 3。

> 本阶段只拆分阶段 1–3 已裁定的实现与验证工作，不新增业务范围、外部技术选型、数据模型或接口契约。已有代码和验证记录仅作为依赖证据，不因本表重新授权未批准的编码范围。

## 1. 模块边界表

| 模块/组件 | 本次职责 | 不负责的内容 | 交付接口/结果 |
| --- | --- | --- | --- |
| 候选人资料准备（CHG-2026-020） | 接收候选人上传、创建归属明确的正式简历，并在同一事务中创建/复用 queued `AsyncTaskRun`，交接固定 `ResumeParseRequestV1` | 不调用 G3 Service/Dispatcher/Worker，不读取正文、不执行解析、不写入画像或解析终态 | `ResumeParseRequestV1` |
| 简历解析与候选人画像 | 受控读取；异步编排；校验 MinerU/Qwen 输出；原子写入画像、简历终态和任务终态；提供本人画像查询 | 不上传文件、不自动脱敏、不做 OCR、不提供重跑/历史版本/批量运营、不解析岗位 JD | `CandidateProfile`、`parse_status`、脱敏 `failure_code` |
| 异步执行基础设施 | Dispatcher 投递、Celery Worker 消费、租约、有限重试、重复/迟到消息围栏 | 不承载业务决策、不启用 Result Backend | `async_task_runs` 终态 |
| 受控对象存储 | 按 Repository 授权读取已 `ready` 的 PDF | 不向 API、Prompt、日志暴露对象键、路径或正文 | 内存 PDF/受控临时文件 |
| MinerU/Qwen 适配器 | PDF → Markdown → 严格结构化画像，并执行 Pydantic/业务规则校验 | 不持久化原文；未校验模型输出不得入库；不猜测补全目标职位 | `ResumeProfileExtractionV1` |

## 2. 技术能力地图与依赖图

```text
CurrentIdentity/归属 → G2 资源事务 → queued AsyncTaskRun/ResumeParseRequestV1 → DocumentParsingRepository
                                      ├→ PostgreSQL（简历/任务/画像/租约）
                                      ├→ 受控对象存储（PDF）
                                      └→ Dispatcher → Redis → Celery Worker
                                                        ├→ MinerU MCP（PDF→Markdown）
                                                        ├→ Qwen Plus（Markdown→JSON）
                                                        └→ Pydantic/业务规则 → 原子终态
                                                               ↓
                                           CandidateProfile/简历状态/任务状态
```

执行顺序：T1 已锁定契约引用检查 → T2 Repository/状态机 → T3 Worker/租约 → T4 解析链路 → T5 原子终态 → T6 集成验收 → T7 门禁材料。任一任务发现新的范围、授权、依赖、字段、状态机或跨模块契约变化，立即标记 `blocked` 并回退到对应阶段重新裁决。

## 3. 任务清单

| 顺序 | 任务 | 类型 | 技术能力 | 本次方式 | 依赖 | 预估 | 状态 | 验收条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | 验证已锁定 `ResumeParseRequestV1@v1` 的引用、生产者/消费者角色、联合门禁和资源权限链 | 业务 | 契约注册表、CurrentIdentity、Repository | 只核对已锁定版本，不重新裁决字段或边界 | 阶段 3 通过 + 契约 locked | ≤2h | 已完成 | 验收只确认双方引用相同文件、版本、哈希和门禁标识；不得在阶段 4 重新决定任务创建方、字段或触发语义 |
| T2 | 核对 Repository 数据访问、简历/任务状态机及租约边界 | 技术使能 | PostgreSQL、Repository、状态机 | 复用既有设计 | T1 | ≤3h | 已完成 | Service/Worker 无 ORM Session、SQL 或直接文件访问；合法迁移、令牌匹配、租约清理和失败终态有明确实现位置 |
| T3 | 固化 Dispatcher → Redis → Celery Worker 的任务输入、领取和重试边界 | 技术使能 | Dispatcher、Redis、Celery、租约 | 复用并联调 | T1、T2 | ≤4h | 已完成 | 固定任务名只接收 `task_run_id`；Worker 先领取租约；重复、迟到、重投递和软超时不产生重复画像或永久运行态 |
| T4 | 执行受控解析链路：对象读取 → MinerU → Qwen → Schema/业务校验 | 业务 | 对象存储、MinerU、Qwen、Pydantic | 复用适配器并集成 | T2、T3 | ≤4h | 已完成 | 仅使用脱敏 PDF；Markdown 不落库；`target_job_titles` 非空；未知字段使用 `null`/空数组 |
| T5 | 核验成功、确定性失败、可重试失败和重试耗尽的原子终态 | 业务 | Repository 事务、状态机、幂等 | 复用设计并补齐边界 | T3、T4 | ≤4h | 已完成 | 成功只产生一份完整画像并同时收敛简历/任务；失败不产生画像；旧令牌和重复消息不覆盖终态 |
| T6 | 完成运行时集成验收、故障恢复验证和脱敏证据归档 | 集成验证 | PostgreSQL、Redis、Celery、MinerU、Qwen | 真实依赖验证 | T5 | ≤4h | 已完成 | 覆盖成功、对象不可用、超时、429/5xx、不可读 PDF、Schema 失败、重试耗尽、Worker 接管和越权查询；证据不含敏感原值 |
| T7 | 更新实现/验证记录并提交阶段 4 关闭材料 | 治理 | Harness stage-gates、变更证据 | 文档交付 | T6 | ≤2h | 已完成 | 计划、实现记录、测试报告和阶段台账一致；未完成依赖不伪记为通过 |

## 4. 阶段 4 完成门槛与本次结论

- 每项任务不超过 4 小时，依赖和执行顺序明确。
- 不包含新的 LLM、第三方 API、队列、对象存储或数据模型选型。
- 阶段 5 只能执行本表授权任务；阶段 4 通过不等于模块完成或可上线。
- 参与包阶段 3、契约锁定、联合批准和 `contract_hash` 已复核一致。

本任务拆分已完成，T1–T7 已按顺序执行并完成实现、验证和证据归档；阶段 5、阶段 6 的通过状态以阶段台账和对应证据为准，阶段 7 代码评审仍需单独执行。

> 岗位 JD 的启动导入与结构化抽取不属于本变更，必须另建变更包并重新完成技术路线、Schema 和失败处理裁决。
