# 后端旧资产盘点

> 本文档记录后端旧资产的实现证据、迁移结果和剩余风险。归档材料只用于追溯，不是当前事实源。

## 1. 证据口径

| 状态 | 含义 |
| --- | --- |
| reusable | 当前代码、迁移或测试提供可复用证据 |
| partial | 部分存在，但仍需按具体 Slice 复核或补充真实验证 |
| missing | 当前代码和迁移中不存在 |

实现证据优先级：当前代码/迁移 → 当前测试结果 → 当前 Slice 契约 → 活动后端文档 → 历史归档。

## 2. 当前代码资产

| 能力 | 证据 | 状态 | 边界 |
| --- | --- | --- | --- |
| 认证与 Candidate 身份 | auth API、security/identity、User/Candidate Repository 和测试 | partial | 当前只确认 User/Candidate，不推导完整 HR 角色 |
| 候选人资料 | candidate_preparation API、Service、Repository、Schema 和测试 | partial | 已有上传/查询，不代表删除和全部前端行为完成 |
| 简历解析 | document_parsing、Worker、Finalization、MinerU/Qwen 适配器 | partial | 单元测试存在，真实外部完整链路仍需 Slice 证据 |
| 异步任务 | Celery、Dispatcher、Worker、AsyncTaskRun Repository | partial | 配置和代码不等于真实重投递、租约及幂等全部通过 |
| 本地对象存储 | local/cleanup 适配器、ObjectStorageRepository 和测试 | reusable | 只适用于本地 Demo，不代表云文件平台 |
| 公共运行底座 | config、logging、exceptions、runtime health、database/redis | reusable | 不代表生产部署和完整观测能力 |
| 岗位、目标、匹配、投递、沟通 | Job/JobGoal/Match/Application/ProgressEvent 及 S10 Conversation/Message/AgentTurn/MessageAttachment Model、Repository、API 和迁移 | partial | S10-01 已交付；S10-02 文件名匹配、附件生命周期、下载和权限核心能力已通过，但真实前端展示整改待回归；S10-03 主动 query 和资料删除仍按后续 Slice 增量实现 |

## 3. 数据与测试资产

| 资产 | 当前事实 |
| --- | --- |
| Alembic | 0001 → 0002 → 0003 → 0004 单链 |
| 当前 Model | User、Candidate、StoredFileObject、Resume、CandidateProfile、CandidateDocument、AsyncTaskRun、Job、JobGoal、AgentRunContext、Match、Application、ProgressEvent、Conversation、Message、AgentTurn |
| 单元测试 | 覆盖认证、资料、解析、异步、存储和架构边界 |
| 集成测试 | PostgreSQL/Redis 与应用运行依赖；需要隔离环境显式执行 |
| 外部测试 | MinerU/Qwen 与完整解析链；需要受控样本和真实凭证显式执行 |

历史测试统计只证明当时测试集，不作为当前运行结果重复引用。

## 4. 文档迁移结果

| 旧资产类别 | 当前事实源 | 迁移结果 |
| --- | --- | --- |
| 工程结构与代码规范 | backend-architecture.md、backend-guidelines.md | 只保留当前目录、分层、响应、异常和 Repository 规则 |
| MVP 范围与技术治理 | backend-delivery-scope.md、backend-development-decisions.md | 当前范围和长期原则已分层 |
| 领域、业务规则和状态 | domain-model.md、business-rules.md | 只迁移当前实体、归属、状态和跨 Slice 规则 |
| 数据模型 | database-design.md | 只迁移当前 Model、枚举和 Alembic 链 |
| 异步、Agent 和对象存储 | architecture 目录 | 当前实现与条件启用边界已分开 |
| MinerU/Qwen | external-capabilities.md、spikes/mineru-validation.md | 适配器证据与真实验证状态已分开 |
| 开发环境和故障案例 | 后端 README、backend-troubleshooting.md | 只保留当前配置和脱敏案例 |
| 旧全量 API、未来实体和未实现方案 | 无 | 未迁移并删除，等待具体 Slice 重新确认 |

## 5. 历史归档

| 路径 | 内容 | 使用边界 |
| --- | --- | --- |
| archive/changes | CHG-2026-001 至 CHG-2026-021、模板和旧校验工具 | 只作历史证据，不转换为当前任务 |
| archive/contracts | ResumeParseRequestV1 注册、契约和联合评审 | 保留旧锁定证据，不能替代当前 Slice Handoff Contract |

归档文件保持原内容和旧路径文字。继续相关能力开发时，由当前 Slice 重新判断证据适用性。

## 6. 当前风险

| 风险 | 当前处理 |
| --- | --- |
| User/Candidate 与正式 HR/求职者角色关系未完成实现对齐 | 在认证相关 Slice Design 中裁决 |
| MinerU/Qwen 完整真实链路证据不足 | 保持 partial，在解析 Slice Readiness Check 中验证 |
| Dispatcher/Worker 真实重投递和接管证据需要复核 | 在首个实际异步 Slice 中验证 |
| 旧契约仍绑定旧开发包边界 | 只保留归档；当前 Producer Slice 重新定义 Handoff |
| S10-02 前端展示、S10-03 及通用沟通平台仍有后续工作 | S10-02 核心附件能力已实现但当前场景 `integration_blocked`，先完成成功提示语移除和仿微信文件卡片整改；S10-03 和通用 Agent Workflow 边界由后续 Slice 重新确认 |

## 7. 盘点边界

- 代码和迁移是当前实现事实，文档不能单独证明能力已实现。
- 当前事实源不复制归档中的未来设计。
- reusable 只表示有可复用证据，不表示满足下一个 Slice 的完整验收。
