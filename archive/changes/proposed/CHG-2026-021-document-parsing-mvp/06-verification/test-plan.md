# 验证计划

- 简历运行时：隔离 PostgreSQL、Redis、Dispatcher 与真实 Celery Worker，验证发布、领取租约、重复/迟到消息无副作用。
- 简历全链路：显式启用外部集成，以受控脱敏 PDF 验证 MinerU、Qwen、Pydantic/业务校验及原子画像/终态；不记录原文、路径、凭证或原始响应。
- 简历故障：存储不可用、Parser 超时、429/5xx、不可读 PDF、Schema 失败、重试耗尽和旧租约写入。
- JD：在契约与数据模型完成后，覆盖请求校验、资源归属、状态迁移、Worker 幂等、成功/失败原子终态和真实依赖链路。
- 回归：每个实现子任务运行 Ruff、完整单元测试；真实依赖门禁未配置时显式 `skipped`/`blocked`，不得记为通过。
