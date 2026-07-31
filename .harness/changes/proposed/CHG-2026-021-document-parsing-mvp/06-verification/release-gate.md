# 简历解析验收报告与发布门禁

**裁定日期：** 2026-07-28  
**裁定范围：** `CHG-2026-021` 的简历解析切片（子任务 1.1–2.4）；不包含岗位 JD 解析。

## 门禁裁定

| 门禁 | 结果 | 证据与裁定 |
| --- | --- | --- |
| 范围与模块边界 | 通过 | 简历解析仅消费版本化 `ResumeParseRequestV1`，候选人资料准备不读取文档、不执行 Worker、不拥有画像或终态。 |
| Repository、归属与状态机边界 | 通过 | 静态复核未发现 Service 或 Worker 直接访问 `AsyncSession`、编写 SQL 或直接读写文件路径；任务仅接收 `task_run_id`，终态写入受执行令牌保护。 |
| 隔离运行时 | 通过 | PostgreSQL、Redis、Backend、独立 Dispatcher 与 Celery Worker 均在隔离 Compose 拓扑运行；运行时探针、真实发布和租约验证已完成。 |
| 外部成功路径 | 通过 | 受控脱敏 PDF 在 Worker 拓扑完成 MinerU → Qwen → 严格 Schema/Pydantic → 原子画像、简历和任务终态；未记录原文、凭证、路径或原始响应。 |
| 故障与恢复 | 通过 | 真实对象缺失验证有限重试后进入 `storage_unavailable` 终态；真实租约验证旧令牌和重复领取无副作用；超时、429/5xx、不可读 PDF、Schema 失败与重试耗尽具备受控故障分支覆盖。 |
| 代码质量 | 通过 | Ruff 通过；完整回归为 `136 passed, 9 skipped`，总覆盖率 81.84%。 |
| 变更包仓库校验 | blocked | `python .harness/changes/tools/validate_changes.py` 被独立的 `CHG-2026-019-upload-idempotency-contract` 缺少 `change.yaml` 和 `01-analysis/impact-analysis.md` 阻断；本变更不得将该仓库级门禁标记为通过。 |
| 简历解析模块完成 | passed（本地 MVP 验收） | 简历解析子任务 2.1–2.4 均已完成；岗位 JD 的启动导入与结构化抽取不属于本变更。 |

## 发布结论

- **简历解析切片：通过本地 MVP 验收。** 可作为后续岗位匹配等模块的“已成功解析简历 + 已校验画像”输入。
- **仓库级发布：blocked。** 在 CHG-019 补齐并使变更包校验通过前，不得宣称仓库级发布门禁通过。
- **简历解析模块：本地 MVP 验收通过。** 岗位 JD 的启动导入与结构化抽取应在岗位管理的后续第 5 步单独裁定和验收。

## 运行与回滚边界

- 当前验证仅适用于隔离本地 Compose 环境与脱敏测试数据；不构成公开生产发布授权。
- 停止本地验证环境可使用 `docker compose -f docker-compose.integration.yml down`；不得在未确认目标为隔离测试卷时使用 `-v`。
- 代码或配置回退遵循变更管理与 Git 回退流程；本次未新增数据库 Schema，未产生额外数据库回滚对象。
