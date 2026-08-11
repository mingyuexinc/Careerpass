# Careerpass 后端入口

## 1. 当前状态

当前后端处于旧资产盘点完成、建立新开发基线并准备前端能力映射的阶段。正式前端已经完成，后端后续按前端用户流程、后端差距分析（Gap Analysis）和垂直切片（Vertical Slice）增量开发。

本项目是受控演示项目（Demo），不因未来生产需要提前建设公开运营、多租户、高并发、灾备或通用平台能力。

## 2. 文档分层职责

| 文档层 | 回答的问题 | 后端工程中的职责 |
| --- | --- | --- |
| `.harness/` | AI 怎样开发？ | 提供 AI Coding 工作流和 Slice Skill |
| 根 `AGENTS.md` | 整个项目从哪里进入？ | 提供项目导航和跨工程红线 |
| `careerpass-frontend/AGENTS.md` | 前端开发先看什么？ | 提供前端约束和前端文档导航 |
| `careerpass-backend/AGENTS.md` | 后端开发先看什么？ | 提供后端约束和后端事实源导航 |
| `careerpass-frontend/docs/` | 前端应该是什么？ | 定义页面、用户流程、UI、架构、组件和交互 |
| `careerpass-backend/docs/` | 后端应该是什么？ | 定义领域、应用程序接口（API）、数据库、工作流和垂直切片（Vertical Slice） |
| `careerpass-backend/app/` | 后端现在实际是什么？ | 当前 FastAPI、服务、仓储、模型、任务和基础设施实现 |

`.harness/` 的执行规则、前端文档的页面事实和后端文档的服务端事实不得相互替代。代码和迁移是当前实现证据，文档不能单独证明能力已经实现。

## 3. 后端不可违反约束

- 数据访问必须经过仓储层（Repository）；服务层（Service）、智能体和工作流不得直接访问对象关系映射会话或编写 SQL。
- 所有用户资源必须校验当前用户和资源归属，不能仅凭资源标识读取或修改。
- 大语言模型（LLM）输出必须经过结构化和业务规则校验后才能入库或驱动流程。
- 状态变化必须遵守合法状态迁移；异步任务在实际使用时必须可追踪、幂等并能表达终态。
- 日志、追踪和响应不得暴露凭证、敏感原文、完整内部定位或模型原始响应。
- 工具输入必须校验，外部调用必须设置超时和错误处理；模型不得拼接 SQL、Shell 命令或未经校验的外部请求。
- API 响应遵循 `{code, msg, data}` 统一结构。

## 4. 后端事实源导航

### 疑难问题首要依据

涉及后端环境、依赖、数据库、Docker、架构、联调或故障排查时，必须先阅读 [`docs/development/backend-troubleshooting.md`](docs/development/backend-troubleshooting.md)。该文档是后端疑难问题的首要诊断依据；已有案例适用时先复用其路径，再进行新增检查。

### 长期决策和工程原则

| 文档 | 用途 |
| --- | --- |
| [`docs/decisions/backend-development-decisions.md`](docs/decisions/backend-development-decisions.md) | 长期后端开发原则、契约优先（Contract-First）、垂直切片（Vertical Slice）、测试反馈和架构边界 |
| [`docs/development/backend-guidelines.md`](docs/development/backend-guidelines.md) | 具体代码分层、命名、异常、测试和实现规范 |

### 当前版本和能力

| 文档 | 用途 |
| --- | --- |
| [`docs/product/backend-delivery-scope.md`](docs/product/backend-delivery-scope.md) | 当前后端版本交付范围、非目标和延期能力 |
| [`docs/product/backend-capability-map.md`](docs/product/backend-capability-map.md) | 正式前端流程到后端 API、业务能力、异步任务和工作流的映射 |
| [`docs/product/business-rules.md`](docs/product/business-rules.md) | 跨页面、跨模块和跨垂直切片共享的业务规则 |
| [`docs/development/backend-asset-inventory.md`](docs/development/backend-asset-inventory.md) | 后端旧资产、证据、状态、迁移去向和冲突清单 |
| [`docs/development/backend-gap-analysis.md`](docs/development/backend-gap-analysis.md) | 现有后端能力与正式前端需求之间的差距分析（Gap Analysis） |
| [`docs/development/vertical-slice-plan.md`](docs/development/vertical-slice-plan.md) | 垂直切片（Vertical Slice）总体开发顺序、依赖和状态 |

### 接口、领域和数据

| 文档 | 用途 |
| --- | --- |
| [`docs/development/slices/`](docs/development/slices/) | 具体 Slice 的 API、异步任务、状态和错误契约；契约只在实际使用它的 Slice 中锁定 |
| [`docs/domain/domain-model.md`](docs/domain/domain-model.md) | 已被当前版本或具体切片确认的领域模型及其状态、合法迁移 |
| [`docs/data/database-design.md`](docs/data/database-design.md) | 已被迁移、代码或具体切片确认的数据库设计 |

### 架构和外部能力

| 文档 | 用途 |
| --- | --- |
| [`docs/architecture/backend-architecture.md`](docs/architecture/backend-architecture.md) | 后端分层、模块依赖和代码目录职责 |
| [`docs/architecture/agent-workflow-architecture.md`](docs/architecture/agent-workflow-architecture.md) | 智能体工作流（Agent Workflow）的控制关系和授权边界 |
| [`docs/architecture/async-task-architecture.md`](docs/architecture/async-task-architecture.md) | FastAPI、Dispatcher、Redis、Celery 和任务状态之间的职责 |
| [`docs/integrations/external-capabilities.md`](docs/integrations/external-capabilities.md) | 外部能力总览、用途、验证状态和限制 |
| [`docs/integrations/spikes/`](docs/integrations/spikes/) | 需要独立验证的外部能力专项记录 |
| [`docs/development/backend-troubleshooting.md`](docs/development/backend-troubleshooting.md) | 后端环境、依赖和联调故障案例 |

### 当前垂直切片

| 文档 | 用途 |
| --- | --- |
| [`docs/development/slices/`](docs/development/slices/) | Slice 规格模板及各垂直切片的范围、契约、方案、任务、测试和完成标准 |

## 5. 后端开发阅读顺序

处理后端任务时：

1. 阅读根 `AGENTS.md` 和本文件；
2. 涉及疑难环境、依赖、数据库、Docker、架构或联调问题时，立即阅读 `docs/development/backend-troubleshooting.md`；
3. 阅读后端开发决策和当前旧资产盘点；
4. 涉及版本范围时阅读后端交付范围；
5. 涉及正式前端接入时阅读前端流程文档和后端能力映射；
6. 阅读当前垂直切片规格及其内嵌的应用程序接口、异步任务和状态契约，以及相关领域/数据事实；
7. 编码前确认当前 Slice Gate 和 Handoff Contract，不得以旧代码或归档材料代替门禁证据。

## 6. 当前工作边界

- 新后端文档中的占位文件不构成已确认事实。
- `archive/` 中的旧变更包和契约只保留为历史证据，不直接转换为新的垂直切片任务清单。
- 领域模型（包括状态和合法迁移）与数据库设计按具体垂直切片（Vertical Slice）增量确认，不提前实现旧文档中的完整未来模型。
- 真实前端接入必须依赖具体 Slice 中锁定的应用程序接口契约（API Contract），不能通过前端临时业务逻辑掩盖后端契约问题。
