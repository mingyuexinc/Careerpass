# 测试报告

## 子任务 2.1：隔离运行时验证

2026-07-28 已在本地隔离 Docker Compose 拓扑完成 PostgreSQL、Redis、独立 Dispatcher 与 Celery Worker 的运行时验证。

- PostgreSQL 就绪检查通过，Redis 返回 `PONG`；Backend readiness 返回统一成功响应。
- Compose 已声明独立 `dispatcher` 服务；Dispatcher 与 Worker 均使用同一隔离 PostgreSQL/Redis 拓扑。
- 固定、无业务副作用的 `careerpass.runtime_probe` 已由真实 Celery Worker 消费并成功完成；Worker 同时注册受控的 `careerpass.resume_parse` 任务。
- `RUN_INTEGRATION_TESTS=true uv run pytest --no-cov -m integration`：6 passed。该用例以真实 PostgreSQL/Redis 验证可靠发布、执行租约领取、重复领取拒绝、旧执行令牌拒绝释放，以及超期租约的安全终态处理。
- 完整质量回归：Ruff 通过；`uv run pytest`：135 passed、8 skipped，覆盖率 81.73%。

## 边界与后续门禁

子任务 2.1 本身不调用 MinerU 或 Qwen，不读取受控 PDF，也不写入候选人画像；其结果不替代下方子任务 2.2 的外部全链路验收。子任务 2.3 继续覆盖存储不可用、外部超时、429/5xx、不可读 PDF、Schema 失败、重试耗尽和旧租约等完整故障链路。

## 子任务 2.2：真实 MinerU → Qwen → 原子画像/终态全链路

2026-07-28 已在本地容器化 Worker 拓扑完成一次显式开启的外部集成验收。

- Worker 显式注入 MinerU/Qwen 凭证；Backend 与 Worker 通过隔离命名卷共享受控对象目录。凭证仅检查存在性，未记录值。
- MinerU stdio Bridge 与 Qwen Plus 均先使用受控样本复核。宿主机一次 MinerU 调用曾返回安全的 `file_unreadable` 分类；在正式 Linux Worker 拓扑复核后，`MineruMcpAdapter` 成功得到非空 Markdown。最终以 Worker 拓扑结果裁定该能力通过。
- `RUN_EXTERNAL_INTEGRATION_TESTS=true RUN_RESUME_PARSE_PIPELINE_TESTS=true uv run pytest --no-cov tests/external/test_resume_parse_pipeline_external.py`：1 passed。测试通过真实 API 上传仓库内受控 PDF，轮询简历至 `succeeded`，并确认候选人仅能查询到已验证画像及非空 `target_job_titles`。
- 该路径实际经过 Dispatcher、Celery Worker、MinerU、Qwen、严格 Schema/Pydantic 校验和 lease-guarded 原子持久化；没有输出或持久化 PDF 正文、Markdown、临时路径、凭证或供应商原始响应。

## 子任务 2.3：真实故障链路与恢复验证

2026-07-28 已完成隔离故障验证；每项证据仅按其实际验证层级记录。

- 真实容器链路：暂停 Dispatcher 后上传唯一受控测试对象，删除该对象并恢复 Dispatcher。真实 Worker 经有限重试后将简历安全置为 `failed / storage_unavailable`；测试结束时 Dispatcher 已恢复运行。未删除既有对象或读取任何文件内容。
- 真实 PostgreSQL/Redis 租约链路：隔离集成测试验证同一任务不能重复领取、旧执行令牌不能释放新租约、过期 `running` 租约仅由 Dispatcher 安全收口为 `failed / internal_error`。终态与关联简历保持一致。
- 受控故障分支：`ResumeParseWorkerService`、MinerU 和 Qwen 适配器单元测试覆盖超时、429/5xx、不可读 PDF、空/非法 Markdown、Schema/Pydantic 失败与重试耗尽。替身仅用于这些可重复的故障分支分类，不替代已完成的真实依赖连通性或 2.2 成功路径验收。
- 失败路径不写入画像；重复或迟到消息因租约/令牌不匹配返回无副作用。完整回归：Ruff 通过；`uv run pytest`：136 passed、9 skipped，覆盖率 81.84%。

## 后续门禁

子任务 2.4 已完成，详细裁定见 `release-gate.md`。简历解析模块通过本地 MVP 验收；仓库级发布仍因独立 CHG-019 的变更包缺失而 `blocked`。岗位 JD 的启动导入与结构化抽取不属于本变更。
