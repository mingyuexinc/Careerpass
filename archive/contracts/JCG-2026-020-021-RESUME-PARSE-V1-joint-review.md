# CHG-020 / CHG-021 联合契约评审记录

## 评审对象

- 联合门禁：`JCG-2026-020-021-RESUME-PARSE-V1`
- 契约：`ResumeParseRequestV1@v1`
- 唯一契约文件：`.harness/contracts/resume-parse-request-v1.yaml`
- 生产者：CHG-020 候选人资料准备
- 消费者：CHG-021 简历解析与候选人画像
- 评审依据：两包最新需求、影响分析、方案设计、任务拆分和阶段台账

## 评审结论

技术边界已完成联合对齐，当前没有发现字段、触发方、任务创建方、事务边界、幂等、权限、状态或安全语义冲突。统一裁决如下：

| 评审项 | 联合裁决 | 结果 |
| --- | --- | --- |
| 字段 | 仅 `candidate_id`、`resume_id`、`task_version="v1"`；`extra="forbid"` | 通过 |
| 身份来源 | `candidate_id` 由 G2 从 `CurrentIdentity` 获取，不接受客户端替换 | 通过 |
| 触发语义 | G2 在正式简历上传、归属校验和对象 `ready` 后，在同一 PostgreSQL 事务中创建/复用 queued 任务 | 通过 |
| 任务责任 | G2 是唯一任务创建/复用方；G3 不创建第二个任务 | 通过 |
| G2 边界 | G2 不调用 G3 Service、Dispatcher、Worker、MinerU 或 Qwen | 通过 |
| G3 边界 | G3 只消费已有 queued 任务，重新校验归属/对象状态，并负责解析、画像和终态 | 通过 |
| 事务 | G2 原子提交对象元数据、Resume、上传幂等关系和 queued `AsyncTaskRun`；G3 独立提交解析结果和终态 | 通过 |
| 幂等 | 同一 `resume_id + task_version` 只保留一个有效任务；重复交接复用，不创建第二个任务 | 通过 |
| 状态 | G2 返回 `201 / UPLOAD_ACCEPTED` 与 `parse_status=processing`；G3 推进 `succeeded/failed` | 通过 |
| 权限 | Repository 重新校验候选人归属、简历归属和对象 `ready`；契约不携带授权信息 | 通过 |
| 安全 | 不传路径、URL、对象键、正文、凭证、模型/MCP 参数或自由指令；诊断信息脱敏 | 通过 |
| 失败隔离 | G2 交接失败回滚并清理未引用对象；G3 失败不回滚已提交的 G2 资源 | 通过 |
| 阶段门禁 | 契约锁定后双方分别通过阶段 3，阶段 4 才可开始；阶段 4 不再裁决契约 | 通过 |

## 文档一致性检查

- CHG-020 与 CHG-021 均引用同一契约文件、版本和联合门禁 ID。
- CHG-020 任务拆分将 queued 任务创建/复用列为 G2 阶段 4 方向。
- CHG-021 任务拆分将 T1 限定为验证已锁定契约引用，不重新决定字段或责任。
- CHG-021 的 `02-design/design.md` 已标记为历史摘要；`03-design/design.md` 为唯一权威方案。
- 既有实现和验证记录已标记为历史证据，不得直接恢复阶段 4/5。

## 锁定状态

两方开发者已确认本次联合技术评审结论并批准 `ResumeParseRequestV1@v1`。契约内容不得原地修改；任何语义变化必须创建新版本，或按跨开发包回退规则重新评审。

| 参与包 | 角色 | 批准状态 | 批准日期 |
| --- | --- | --- | --- |
| CHG-2026-020-candidate-profile-preparation-mvp | producer | approved | 2026-08-01 |
| CHG-2026-021-document-parsing-mvp | consumer | approved | 2026-08-01 |

当前状态：`locked`。CHG-020 与 CHG-021 阶段 3 均已由开发者人工复核通过；阶段 4 尚未启动，阶段 5 仍冻结。

契约文件 SHA-256：`9AB937AE08E4A69C3D1D87C1968B8C17D7B6371984E236B1481C984F49EC9B18`
