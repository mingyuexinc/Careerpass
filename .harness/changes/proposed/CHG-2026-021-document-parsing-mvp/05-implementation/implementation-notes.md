# CHG-021 实现记录

## 1. 实现范围与门禁

本记录对应 CHG-021 阶段 5 的 T1–T5 实现、阶段 6 的 T6 验证以及 T7 材料闭环。实现严格复用阶段 1–3 已批准的 `ResumeParseRequestV1@v1`，未修改契约版本、契约哈希、数据模型、状态机或跨包职责。

阶段 4 已完成并通过，参与开发包和联合契约门禁均已满足。阶段 5 仅执行任务拆分中已授权的 T1–T5；阶段 6 使用真实 PostgreSQL、Redis、Dispatcher、Celery Worker、MinerU 和 Qwen 依赖验证。

## 2. T1–T5 实现结果

| 任务 | 实现结果 | 主要证据 |
| --- | --- | --- |
| T1 | 已复核 `ResumeParseRequestV1@v1` 的注册表、双方角色、联合门禁、归属校验和固定任务输入边界 | `.harness/contracts/resume-parse-request-v1.yaml`、`.harness/contracts/JCG-2026-020-021-RESUME-PARSE-V1-joint-review.md` |
| T2 | 已通过 Repository 访问 PostgreSQL 资源；解析 Service/Worker 不直接持有 ORM Session、SQL 或对象存储访问；状态迁移和租约边界由 Repository/Service 负责 | `app/repositories/document_parsing_repository.py`、`app/services/document_parsing_service.py` |
| T3 | 已固化 `careerpass.resume_parse` 只接收 `task_run_id`，Worker 先领取租约，重复/迟到消息和重试受令牌、租约与终态围栏约束 | `app/infrastructure/tasks/dispatcher.py`、`app/infrastructure/tasks/worker.py`、`app/services/resume_parse_worker_service.py` |
| T4 | 已完成受控对象读取、MinerU Markdown 提取、Qwen 结构化输出、Pydantic 与业务规则校验；Markdown、原文、供应商原始响应不落库或进入非必要响应 | `app/infrastructure/mineru_mcp.py`、`app/infrastructure/qwen_profile.py`、`app/schemas/document_parsing.py` |
| T5 | 已完成成功、确定性失败、可重试失败和重试耗尽的原子终态处理；成功仅写入一份完整画像，失败不写入画像，旧令牌/重复消息不能覆盖终态 | `app/services/resume_parse_finalization_service.py`、`tests/unit/test_resume_parse_finalization_service.py`、`tests/unit/test_resume_parse_worker_service.py` |

## 3. 关联实现补齐

外部全链路复核发现，既有 G2 简历列表实现未返回协议要求的 `parse_status`。已在 CHG-020 的既有响应映射中补齐 `parse_status`，并仅在失败时返回脱敏 `failure_code`；该修复与既有接口协议一致，不改变 `ResumeParseRequestV1@v1` 或其哈希。对应 Schema、Service、API 和测试已同步更新。

## 4. T6 验证结论

2026-08-02 使用 Docker Compose 真实依赖完成验证：

- PostgreSQL/Redis/Dispatcher/Worker 运行时集成测试：6 项通过。
- MinerU 外部适配器、Qwen 外部适配器和真实解析全链路：通过。
- 全量测试（含真实集成与外部解析开关）：148 项通过，覆盖率 89.64%，达到项目 80% 门槛。
- Ruff 静态检查：通过。
- 复核成功、对象不可用、超时、供应商错误、不可读 PDF、Schema 失败、重试耗尽、重复/迟到消息、租约接管和归属查询边界；证据仅记录状态、失败分类和关联 ID，不记录凭证、简历原文、Markdown、模型原始响应或完整路径。

一次复跑曾出现 PostgreSQL 长连接类型缓存失效，重启应用侧容器刷新连接后，外部链路和最终全量覆盖率测试均稳定通过；该环境处置不改变业务实现。

## 5. 交付结论

T1–T7 已按任务清单完成。CHG-021 阶段 5、阶段 6 的证据已分别归档至阶段台账；阶段 7 代码评审仍按十一阶段流程保持未启动，不能由本记录替代。
