# 测试计划（历史证据与后续阶段 6 草案）

> 现有条目包含历史实现验证；当前治理迁移后的阶段 6 必须按 G2 同事务创建/复用 queued `AsyncTaskRun`、G3 只消费既有任务的边界重跑。历史证据不能替代阶段 4/5 门禁。

- 单元：类型白名单、PDF/JPEG 特征、Markdown 编码、对象键不透明性、画像 Schema 和目标职位校验。
- 契约：上传幂等、分页、归属隔离、统一响应与无敏感响应字段。
- 本地集成：隔离 PostgreSQL、Redis、Dispatcher、Worker、对象存储。
- 外部集成：MinerU 子任务显式开启后使用受控脱敏 PDF 调用同机 stdio Bridge 的 `parse_documents`，验证非空 Markdown 和临时文件清理；完整画像原子写入仍须在后续 Qwen Worker 子任务验收。未配置凭证时跳过，不可伪造为通过。
- 外部集成：Qwen 适配器子任务显式开启后，以固定脱敏 Markdown 调用百炼 `qwen-plus`，验证返回值通过 `ResumeProfileExtractionV1` 的严格 JSON Schema 与 Pydantic 校验；不记录 Prompt 或模型原始响应。
- 本地集成：在隔离 PostgreSQL 中领取真实执行租约后，验证成功路径原子写入画像、简历和任务终态；验证失败路径不创建画像；验证已完成或旧令牌的迟到写入无副作用。
- 子任务 8 边界：验证 `ResumeParseRequestV1` 拒绝额外字段；候选人资料准备仅通过该请求提交解析；文档解析服务以当前候选人身份查询画像；资料准备实现不得导入画像或终态持久化模型。
- 子任务 8 集成：在隔离 PostgreSQL/Redis 环境运行既有上传、画像隔离和原子终态测试，确认请求提交、画像查询与终态持久化迁移后仍保持同一事务、归属校验和安全 `404`。
- 子任务 9 单元：覆盖固定 Worker 注册、首次领取租约后的成功终态、重复/迟到消息无副作用、MinerU/Qwen 可重试失败先释放租约、`file_unreadable` 直接失败、重试耗尽写入安全失败码。
- 子任务 9 集成：在隔离 PostgreSQL、Redis、Dispatcher 和真实 Celery Worker 下，验证发布的 `careerpass.resume_parse` 消息会领取租约，并在受控替身解析器下完成重试或原子终态；不以该测试替代子任务 11 的真实 MinerU/Qwen 全链路验收。
- 子任务 10（候选人资料准备）：仅验证上传、幂等、受控对象存储、本人资源/状态查询，以及 `ResumeParseRequestV1` 的原子提交和 Dispatcher 可靠投递；不启动或断言 Worker、MinerU、Qwen 或画像结果。
- 子任务 11（文档解析）：验证 Dispatcher → Worker → MinerU → Qwen → Pydantic/业务校验 → 原子画像/终态完整链路，以及存储、超时、429/5xx、不可读文件、Schema 失败、重试耗尽和旧租约的故障路径。真实外部依赖结果必须单独记录，不能由子任务 10 替代。
