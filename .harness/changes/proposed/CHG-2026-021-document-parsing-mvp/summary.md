# 文档解析模块 MVP

## 变更概述

将文档解析作为独立业务模块推进和验收。模块接收经授权、版本化的简历或岗位 JD 解析请求；负责受控读取、结构化提取、Pydantic 与业务规则校验、有限失败分类/重试，以及解析结果与终态的原子持久化和候选人归属查询。

候选人资料准备只负责上传并可靠提交 `ResumeParseRequestV1`；它不读取文档、不执行 Worker，也不拥有候选人画像或解析终态。

## 当前基线

- 简历解析的版本化请求、文档解析 Repository/Service、画像查询、原子终态、MinerU 适配器、Qwen 适配器和 Worker 编排已经实现，并有单元测试证据。
- MinerU 与 Qwen 已在受控脱敏样本上分别完成外部预验证；这不是 Dispatcher → Worker → MinerU → Qwen → 原子终态的真实全链路验收。
- Docker 本地集成环境、PostgreSQL、Redis、独立 Dispatcher 与 Celery Worker 已完成隔离运行时验证；该结果只覆盖发布、消费与租约保护，不替代 MinerU → Qwen 的外部全链路验收。
- 受控脱敏 PDF 已在容器化 Worker 拓扑完成 MinerU → Qwen → 严格 Schema/Pydantic 校验 → 画像/简历/任务原子终态全链路验收；未记录 PDF、Markdown、凭证或供应商原始响应。
- 存储对象缺失的真实容器故障已验证有限重试与 `storage_unavailable` 安全终态；超时、429/5xx、不可读 PDF、Schema 失败、重试耗尽和旧租约均有受控故障分支与真实租约持久化验证。
- JD 解析分支尚未实现，不能因简历分支已实现而视为整个文档解析模块完成。

## 发布门禁结论

- 简历解析切片已通过本地 MVP 验收，详见 `06-verification/release-gate.md`。
- 仓库级变更包校验目前被独立的 CHG-019 缺失必需文件阻断；该门禁为 `blocked`。
- 文档解析模块整体仍为 `blocked`，直到岗位 JD 解析的 3.1–3.4 完成并验收。

## 影响模块

- 文档解析：简历与 JD 的解析请求、结果、终态及查询。
- 异步技术使能：Dispatcher、Celery Worker、租约和受控重试。
- 岗位管理：提交 `JobDescriptionParseRequest` 并接收受校验结果。
- 候选人资料准备：仅作为 `ResumeParseRequestV1` 的上游提交方。

## 关键约束

- 业务 Service/Worker 不得直接访问 ORM Session、SQL 或本地文件路径；读取与持久化均经 Repository 和受控存储抽象。
- Worker 仅接收 `task_run_id`，先领取匹配执行租约；重复或迟到消息不得产生副作用。
- LLM 输出必须先经 Pydantic 和业务规则校验，才可持久化或驱动终态。
- 不记录简历/JD 原文、内部路径、凭证、模型原始响应或含敏感内容的异常堆栈。

## 回滚方案

本次先建立计划和验收边界，不引入运行时代码或数据库变更，无需数据库回滚。后续每项实现变更须随任务提供独立的迁移与回滚证据。
