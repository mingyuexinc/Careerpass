# Careerpass 后端项目入口规则

## 0. 后端任务强制启动门禁

每个新会话中的后端任务都必须先完成以下门禁，不因任务类型、历史结论或已有计划而省略：

1. 第一次仓库读取必须完整包含 [`docs/development/backend-troubleshooting.md`](docs/development/backend-troubleshooting.md)；如第一次工具调用批量读取多个入口文件，该文档必须包含在同一调用中。
2. 完成读取后，在首次工作进度中声明匹配的既有案例和复用的诊断路径；没有适用案例时明确记录“未匹配既有案例”。
3. 门禁完成前，不得制定后端开发结论、判断环境能力、执行依赖诊断或修改代码和文档。
4. 涉及 Docker、Compose、PostgreSQL、Redis、Dispatcher、Worker 或 Readiness Check 时，必须先从后端根目录执行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend-readiness.ps1`，再执行专项检查。
5. `Get-Command docker` 未发现命令、命令不可识别或执行被拒绝，只能说明当前 Shell 的命令发现或执行权限状态；不得据此断言 Docker CLI 未安装、Docker Engine 未运行或当前环境无法验证。
6. 预检返回 `execution_denied` 时，Codex 必须使用授权执行上下文重新运行同一脚本。只有授权上下文中的绝对路径 `docker version` 结果，才能支持 Docker Engine 不可连接的结论。

门禁证据必须进入当前任务记录；涉及 Slice 时还必须写入 `technical-design.md` 的 Readiness 证据。治理回归测试见 `tests/unit/test_backend_governance.py`。

## 1. 项目定位

Careerpass 后端项目负责为正式前端提供可验证的业务能力、领域规则、数据持久化、异步处理和受控外部能力接入。

当前目标是围绕正式前端已经确定的用户流程，按前端优先、Slice 层级的方式逐步交付求职者和 HR 的核心业务闭环。

本项目当前是以面向 VIP 用户进行核心功能和项目亮点演示为目标的受控演示项目（Demo）；非演示环节不纳入当前开发范围，非核心功能遵循最小必要原则设计，不因未来生产需要提前建设公开运营、多租户、高并发、灾备或通用平台能力。正式前端的页面和 Mock 数据只能作为后端能力发现线索，不能单独决定后端领域规则、资源归属、状态拥有者或数据结构。

跨前后端业务语义以 [`../docs/business/business-baseline.md`](../docs/business/business-baseline.md) 为唯一基线；后端技术事实以 `docs/` 中对应事实源、当前代码、Alembic 迁移、测试和已锁定的 Slice 技术设计共同确认；归档目录和旧开发包只用于历史追溯。

## 2. 当前开发阶段

当前状态为后端新开发基线已建立，正在依据正式前端流程、后端能力映射和差距分析，按 Vertical Slice（垂直切片）增量交付：

- 正式前端页面、流程和 Mock 数据已经完成当前版本的主要用户体验；
- 后端技术栈、分层边界、数据访问规则和基础服务基线已经建立；
- S-01 用户登录已完成，已具备统一 User、Candidate/HrProfile 身份和当前身份交接；
- S-02 岗位 JD 上传及后续 Slice 仍需按当前 Gate 重新完成业务规格、技术设计和 Readiness Check；
- 领域模型、数据库设计和业务规则只随具体 Slice 的真实需要增量确认，不提前实现旧文档中的完整未来模型；
- 真实前端接入必须依赖具体 Slice 的 `technical-design.md` 中锁定的契约，不能由前端临时逻辑掩盖后端契约问题。
- 前后端共同使用的请求、响应、状态和错误以 [`../docs/integration/README.md`](../docs/integration/README.md) 及具体 Integration Contract 为准；开发者演示、自测和整改以对应 Integration Scenario 为准。

旧文档、旧代码、Mock、配置存在或历史开发包内容，不等于当前后端能力已经实现。

## 3. 技术基线

| 项目 | 约定 |
| --- | --- |
| 编程语言 | Python 3.12 |
| Web 框架 | FastAPI 0.139.x |
| 数据校验 | Pydantic 2.x |
| ORM | SQLAlchemy 2.0.x |
| 数据库迁移 | Alembic 1.x |
| 主数据库 | PostgreSQL 16.x |
| 缓存与消息基础设施 | Redis 7.4.x |
| 异步任务 | Celery 5.6.x；仅在具体 Slice 需要时启用 |
| 外部能力 | LangChain、LangSmith、Qwen、Pinecone、MinerU 等按 Slice 条件启用，并必须有真实验证证据 |
| 测试 | pytest、真实依赖集成测试和正式前端端到端验证 |
| 代码质量 | Ruff；pytest 默认要求整体覆盖率不低于 80% |
| 运行方式 | uv 管理依赖；Docker Compose 提供隔离集成环境 |

详细分层和运行结构见 [`docs/architecture/backend-architecture.md`](docs/architecture/backend-architecture.md)；本地启动和基础服务验证见 [`README.md`](README.md)。

## 4. 核心开发规则

### 4.1 正式前端与后端分离

- 正式前端的用户流程、页面状态和可观察结果是后端能力发现入口；
- 后端负责确认业务范围、领域事实、资源归属、状态迁移、契约和副作用边界；
- 前端字段、Mock 数据和展示文案不能单独证明后端实体、数据表、状态或授权规则；
- 前后端通过对应 Slice 的版本化技术设计契约协作，不在前端临时增加业务规则来掩盖后端问题。
- Slice 技术设计中的后端 Handoff Contract 不替代跨端 Integration Contract；后端完成不等于 Integration Scenario 已交付。

### 4.2 Slice 与文档分离

每个 Slice 目录采用双文档结构：

```text
slice-<name>/
├── slice-spec.md
└── technical-design.md
```

- `slice-spec.md` 只描述 Goal、Input、Output、Preconditions、Business Rules、Scope / Non-goals、Technical Constraints、Acceptance Criteria 和 Developer Decisions Required；
- `technical-design.md` 记录 API、异步任务、Handoff Contract、领域/数据影响、技术实现、失败处理、验证证据和 Close 结论；
- 每个 Slice 必须关联至少一个 Integration Scenario；跨端契约由 `docs/integration/` 维护，技术设计只引用并记录本 Slice 的实现影响；
- 领域模型、数据库设计和跨 Slice 业务规则分别以全局事实源为准，Slice 技术设计只记录本 Slice 的使用方式和变化；
- 一个 Slice 只能有一个主要业务结果，不能按 Controller、Repository、数据库表或异步组件横向拆分。

### 4.3 分层与数据访问

- Controller 负责协议解析、身份上下文和统一响应，不承载领域编排；
- Service 负责用例编排和业务规则调用，不直接编写 SQL 或访问 ORM Session；
- Repository 负责查询、写入、资源归属校验和持久化边界；
- Infrastructure 负责数据库、缓存、对象存储、消息队列和外部适配器，不拥有业务领域状态；
- Agent 和 Workflow 只能通过已注册、已校验的工具调用业务能力，不得越过 Service/Repository 访问内部实现；
- API 响应统一使用 `{code, msg, data}` 结构。

### 4.4 资源、状态与安全

- 所有用户资源必须校验当前用户和资源归属，不能仅凭资源 ID 读取或修改；
- 每个业务状态必须有唯一状态拥有者，状态变化必须遵守合法迁移，不能直接覆盖状态字段绕过业务规则；
- 密码、令牌、密码摘要、联系方式、简历原文、内部文件定位、模型原始响应和异常堆栈不得进入非必要响应、日志或追踪；
- LLM 输出必须经过 Pydantic 结构化校验和业务规则校验后，才能入库或驱动流程；
- 外部投递、消息发送和其他不可逆副作用必须有明确授权、审计和失败边界；
- 工具输入必须校验，外部调用必须设置超时、错误处理和适用的有限重试。

### 4.5 异步与外部能力

- 异步任务只有在具体 Slice 的业务结果确实需要时才启用；
- 实际使用的任务必须可追踪、幂等、可重试并能表达明确终态；
- PostgreSQL 中的任务记录是业务任务状态事实源，不能以 Redis/Celery 临时结果替代；
- 首次使用的 LLM、解析器、对象存储、队列或第三方服务必须在 Readiness Check 中提供最小真实证据；
- Mock、配置存在、文档说明或单元测试不能替代真实外部能力验证。

## 5. 当前 MVP 范围

当前版本验证一个由求职者和 HR 共同参与、可重复演示的系统内求职闭环。具体版本范围以 [`docs/product/backend-delivery-scope.md`](docs/product/backend-delivery-scope.md) 为准。

### 包含

- 受控求职者和 HR 登录，并建立可信当前身份；
- 求职者简历和其他资料的上传、解析、画像和资料管理；
- 求职目标创建和 Agent 启动条件；
- 受控岗位 JD 提供和岗位数据准备；
- 基于候选人画像、求职目标和岗位的结构化匹配结果；
- 系统内投递记录、投递进度和 HR 对单条投递记录的合法更新；
- 授权范围内的系统内沟通和 Agent 回复草稿或模拟回复；
- 业务资料删除和正式前端闭环接入。

### 不包含

- 公开注册、复杂账号体系、多租户和设备管理；
- 真实招聘平台投递和真实外部消息发送；
- 公开网络爬取、第三方平台同步和生产级外部数据运营；
- 多轮岗位匹配、多目标、多份简历并行管理和实时消息推送；
- 生产级监控、部署、高可用、灾备和通用平台能力；
- 未经当前版本范围和对应 Slice 裁决的未来领域实体、接口、状态和数据表。

## 6. 文档导航

### 文档分层职责

| 文档层 | 回答的问题 | 本工程中的职责 |
| --- | --- | --- |
| `.harness/` | AI 怎样开发？ | 提供前端优先、Slice 层级的 AI Coding 工作流和技能 |
| 根 `AGENTS.md` | 整个项目从哪里进入？ | 提供项目导航和跨工程红线 |
| `careerpass-frontend/AGENTS.md` | 前端开发先看什么？ | 提供前端约束和前端文档导航 |
| `careerpass-backend/AGENTS.md` | 后端开发先看什么？ | 提供后端约束和后端事实源导航 |
| `careerpass-frontend/docs/` | 前端应该是什么？ | 定义页面、用户流程、UI、架构、组件和交互 |
| `careerpass-backend/docs/` | 后端应该是什么？ | 定义版本范围、领域、接口、数据库、架构、外部能力和 Slice 技术事实 |
| `docs/integration/` | 如何跨端交付？ | 定义 Integration Contract、Integration Scenario、联调、自测和整改证据 |
| `careerpass-backend/app/` | 后端现在实际是什么？ | 当前 FastAPI、Service、Repository、Model、任务和基础设施实现 |

`.harness/` 的执行规则、前端文档的页面事实和后端文档的服务端事实不得相互替代。代码、迁移和测试是当前实现证据，文档不能单独证明能力已经实现。

### 产品文档

| 文档 | 用途 |
| --- | --- |
| [`docs/product/backend-delivery-scope.md`](docs/product/backend-delivery-scope.md) | 当前版本目标、范围、非目标和延期能力 |
| [`docs/product/backend-capability-map.md`](docs/product/backend-capability-map.md) | 正式前端流程到后端能力、依赖和证据的映射 |
| [`docs/product/business-rules.md`](docs/product/business-rules.md) | 跨 Slice 持续有效的业务规则 |

### 跨前后端业务事实

| 文档 | 用途 |
| --- | --- |
| [`../docs/business/business-baseline.md`](../docs/business/business-baseline.md) | 当前已确认的跨前后端业务事实、事实编号和待裁决事项 |
| [`../docs/business/business-fact-extraction.md`](../docs/business/business-fact-extraction.md) | 业务事实提取、冲突裁决、更新和 Slice 使用规则 |

### 决策和架构文档

| 文档 | 用途 |
| --- | --- |
| [`docs/decisions/backend-development-decisions.md`](docs/decisions/backend-development-decisions.md) | 前端优先、契约协作、Vertical Slice、分层边界和长期开发决策 |
| [`docs/architecture/backend-architecture.md`](docs/architecture/backend-architecture.md) | 后端运行结构、依赖方向、对象存储和架构变更规则 |
| [`docs/architecture/async-task-architecture.md`](docs/architecture/async-task-architecture.md) | FastAPI、Dispatcher、Redis、Celery 和任务状态职责 |
| [`docs/architecture/agent-workflow-architecture.md`](docs/architecture/agent-workflow-architecture.md) | Agent Workflow 的启用条件、控制关系和授权边界 |

### 领域、数据和外部能力文档

| 文档 | 用途 |
| --- | --- |
| [`docs/domain/domain-model.md`](docs/domain/domain-model.md) | 已确认的领域对象、关系、归属、状态和合法迁移 |
| [`docs/data/database-design.md`](docs/data/database-design.md) | 已由迁移、代码或 Slice 确认的表、关系、约束和事务边界 |
| [`docs/integrations/external-capabilities.md`](docs/integrations/external-capabilities.md) | 外部能力用途、验证状态和限制 |
| [`docs/integrations/spikes/`](docs/integrations/spikes/) | MinerU、Qwen 等需要独立验证的外部能力专项记录 |

### 设计和开发文档

| 文档 | 用途 |
| --- | --- |
| [`docs/development/backend-guidelines.md`](docs/development/backend-guidelines.md) | 代码分层、命名、异常、测试和实现规范 |
| [`../docs/integration/slice-acceptance-testing.md`](../docs/integration/slice-acceptance-testing.md) | 无前端展示结果的内部能力 Slice 验收边界、测试分层和 Acceptance Artifact 规范 |
| [`docs/development/vertical-slice-plan.md`](docs/development/vertical-slice-plan.md) | Slice 候选、依赖、顺序和状态 |
| [`docs/development/slices/slice-spec-template.md`](docs/development/slices/slice-spec-template.md) | Slice 业务规格模板 |
| [`docs/development/slices/slice-technical-design-template.md`](docs/development/slices/slice-technical-design-template.md) | Slice 技术设计模板 |
| [`docs/development/slices/`](docs/development/slices/) | 各 Slice 的业务规格、技术设计、契约、验证和完成结论 |
| [`../docs/integration/README.md`](../docs/integration/README.md) | 跨端契约、交付场景、自测和问题整改规则 |
| [`docs/development/backend-troubleshooting.md`](docs/development/backend-troubleshooting.md) | 后端环境、依赖、数据库、Docker 和联调故障案例 |

## 7. 开发前阅读顺序

完成第 0 节强制启动门禁后，按任务需要继续阅读：

1. 先阅读根 `AGENTS.md` 和本文件。
2. 先阅读 `../docs/business/business-baseline.md` 和 `../docs/business/business-fact-extraction.md`；发现影响当前 Slice 的 `pending` 事实时，不得自行猜测。
3. 复用启动门禁中匹配的 `docs/development/backend-troubleshooting.md` 诊断路径；问题解决后将可复用结论补充回该文档。
4. 涉及版本范围和用户流程时，阅读 `docs/product/backend-delivery-scope.md`、`backend-capability-map.md` 和必要的前端产品文档。
5. 涉及长期技术原则时，阅读 `docs/decisions/backend-development-decisions.md`、`backend-architecture.md` 和 `backend-guidelines.md`。
6. 涉及领域、状态、归属或数据时，阅读 `docs/domain/domain-model.md`、`docs/data/database-design.md` 和 `docs/product/business-rules.md`。
7. 选择或开发 Slice 时，阅读 `docs/development/vertical-slice-plan.md`、当前 Slice 的 `slice-spec.md` 和 `technical-design.md`。
8. 涉及外部能力时，阅读 `docs/integrations/external-capabilities.md` 和对应的 `spikes/` 验证记录。
9. 编码前确认 Slice Gate、Integration Contract、Integration Scenario、Handoff Contract、Repository 边界和真实依赖证据，不得以旧代码或归档材料替代门禁证据。

## 8. AI/Codex 工作规则

### 修改前

- 确认第 0 节强制启动门禁已完成；涉及基础服务时记录统一预检的执行上下文和结果；
- 先判断任务属于业务范围、Slice 文档、后端代码、迁移、测试还是外部能力验证；
- 阅读与任务相关的项目范围、前端流程、领域、数据、架构和故障案例事实源；
- 优先查找并复用现有 Controller、Service、Repository、Model、任务和测试模式；
- 确认当前 Slice 的主要业务结果、Non-goals、依赖、契约和验收条件；
- 确认关联 Integration Scenario 的交付目标、演示数据、预期结果和验证方式；
- 对实现细节是否需要人工确认，使用 `.harness/skills/implementation-decision-autonomy/实现决策自主权.md` 判断。

### 修改中

- 严格按 Slice Select、Slice Design、Readiness Check、Implement、Verify、Close 顺序推进；
- Verify 前后必须执行 Integration Scenario；记录失败问题、回退 Gate、整改和回归结果；
- Slice Design 同时维护 `slice-spec.md` 和 `technical-design.md`；
- 不把 API、数据库表、类、方法和实现流程写入 `slice-spec.md`；
- 不在 Service、Agent 或 Workflow 中直接访问 ORM Session 或编写 SQL；
- 不绕过当前身份和资源归属校验，不绕过状态机，不让 LLM 输出直接驱动事实或副作用；
- 发现产品行为、业务语义、契约、数据边界、状态或关键架构变化时停止受影响实现并回退到对应 Gate；
- 不擅自扩大当前版本范围，不把未证实的旧设计转成代码或全局事实。

### 修改后

- 执行与改动匹配的 Ruff、单元测试、接口测试、集成测试或真实外部验证；
- 验证核心成功路径、非法输入、资源不存在、无权访问、依赖失败、状态迁移、幂等和数据一致性；
- 有前端展示结果的联调任务必须验证真实前端可观察结果；无前端展示结果的内部能力 Slice，必须按声明的测试层验证：核心能力使用 Capability Acceptance 的真实输入、核心输出和 Acceptance Artifact，直接持久化、公共基础设施、跨 Slice 交接和完整用户流程分别由对应专项测试负责；不能只验证后端 Mock；
- `backend_ready` 只能表示后端实现和后端验证通过；只有 Integration Scenario 通过后才能标记 `integration_delivered`；
- 检查 `slice-spec.md` 仍只包含业务内容，`technical-design.md` 与代码、迁移和测试一致；
- 检查全局领域、数据、业务规则和外部能力文档是否需要同步；
- 更新延期项、Handoff Contract 和 Close 结论，运行 `git diff --check`。

## 9. 当前推荐工作顺序

1. 阅读根入口、后端入口、正式前端流程、版本范围、能力映射和差距分析。
2. 完成或复用项目级基础服务基线：Docker Compose、PostgreSQL、Redis、Alembic、Backend 健康检查和前端开发服务器。
3. 依据前端用户流程和后端能力映射选择一个具有单一业务结果的 Slice。
4. 按新模板建立 `slice-spec.md`，确认 Goal、Input、Output、Preconditions、Business Rules、Scope / Non-goals、Technical Constraints、Acceptance Criteria 和 Developer Decisions Required。
5. 建立 `technical-design.md`，锁定 API、异步任务、Handoff Contract、领域/数据影响、关键依赖和 Readiness 证据。
6. 在 Readiness Check 通过后，按现有架构实现完整纵向链路：入口、Service、Repository、数据、任务、外部能力和可观察结果。
7. 完成单元、接口、集成、真实外部能力和前后端端到端验证；发现设计变化时回退，不在实现中静默扩大范围。
8. Close 前同步稳定的领域、数据、业务规则和外部能力事实，确认 Slice 技术设计、代码、迁移、测试和 Handoff Contract 一致。
9. 按当前依赖推进后续 Slice：S-01 用户登录 → S-02 岗位 JD 上传 / S-04 简历上传与解析 / S-05 求职者资料上传 → S-03 JD 信息抽取与 S-06 求职目标 → S-07 Agent 启动 → S-08 匹配与投递 → S-09 投递进度、S-10 AI 沟通；资源创建后按条件推进 S-11 业务资料删除。
