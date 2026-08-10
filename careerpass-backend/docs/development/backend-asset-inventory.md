# 后端旧资产盘点

> 盘点阶段：后端文档重构准备阶段（不属于任何业务 Vertical Slice 的阶段 1–11）。
>
> 盘点范围：仅后端资产。正式前端的消费关系暂不在本清单中裁决，将在后续 `backend-capability-map.md` 与 Gap Analysis 中处理。
>
> 盘点原则：本文件记录资产事实、证据、状态和迁移去向；不移动、删除或重写旧资产，不把文档存在等同于能力已实现。

## 1. 盘点范围与判定规则

### 1.1 纳入范围

- `careerpass-backend/app/`：API、Service、Repository、Schema、Model、Infrastructure、任务和外部适配器。
- `careerpass-backend/tests/`：单元、集成和外部能力测试及其受控 fixtures。
- `careerpass-backend/alembic/`：迁移脚本、迁移链和数据库演进事实。
- `careerpass-backend` 根目录配置：`pyproject.toml`、`Dockerfile`、Compose、环境模板、`alembic.ini`、`uv.lock`。
- `.harness/wiki/` 中与后端业务、数据、架构、异步、对象存储、外部能力和开发环境有关的文档。
- `.harness/contracts/` 中的后端 API、异步任务和跨开发包契约。
- `.harness/changes/` 中与后端实现、数据、契约和技术能力有关的变更包。
- `careerpass-backend/docs/` 当前已创建的占位文档。

### 1.2 首轮不纳入范围

- `careerpass-frontend/` 源代码和前端文档；前端消费关系由后续能力映射和 Gap Analysis 处理。
- 纯项目治理规则、Codex 技能文件和通用变更模板；这些继续由 `.harness/` 管理。
- 与后端无直接关系的产品、设计和原型资产。

### 1.3 状态定义

| 状态 | 判定规则 |
| --- | --- |
| `reusable` | 事实被当前代码、测试、迁移或锁定契约支持，可以迁移或引用。 |
| `partial` | 只有部分内容被证据支持，或需要按 Demo 范围、模块边界或新范式重写。 |
| `obsolete` | 已被当前实现、MVP 范围或新开发范式否定，不应作为新事实源。 |
| `pending` | 证据不足、资产之间冲突或需要后续 Gap/Contract/Slice 裁决。 |

### 1.4 迁移动作定义

| 动作 | 含义 |
| --- | --- |
| `migrate` | 内容稳定，迁移为新的后端全局事实源。 |
| `rewrite` | 内容仍有价值，但必须按新范式和 Demo 范围重写。 |
| `reference` | 新文档只引用旧资产作为历史或验证证据。 |
| `retain` | 继续留在旧位置，不属于后端事实源。 |
| `archive` | 仅保留历史追溯，不参与后续开发。 |
| `do-not-migrate` | 已失效、越界或会误导当前开发，不迁移其内容。 |

## 2. 后端代码资产主清单

代码按能力组盘点；组内文件作为一个可独立裁决的资产单元，避免为每个 Python 文件重复书写同一结论。

| Asset ID | 资产类别 | 原始路径 | 资产摘要与当前证据 | 当前状态 | MVP 适用性 | 新事实源去向 | 处理动作 | 冲突或风险 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BE-CODE-AUTH-001 | code | `app/api/v1/auth.py`; `app/core/{security,identity}.py`; `app/services/{registration,login}_service.py`; `app/repositories/{user,candidate}_repository.py`; `app/schemas/auth.py` | 注册、登录、`/auth/me`、短期 Access Token、User/Candidate 初始化和当前身份解析；对应认证、身份和 Repository 单元测试。 | `partial` | `required` | `docs/architecture/backend-architecture.md`; `docs/domain/domain-model.md`; `docs/contracts/api-contract.md` | `rewrite` | 正式前端包含 HR/求职者角色，但当前后端模型和接口只显式支持 User/Candidate，角色能力待确认。 | 后续 Capability Map 与 Slice Contract 复核角色和认证边界。 |
| BE-CODE-CANDIDATE-001 | code | `app/api/v1/candidate_preparation.py`; `app/services/candidate_preparation_service.py`; `app/repositories/candidate_preparation_repository.py`; `app/schemas/candidate_preparation.py` | 简历和候选人附加资料上传、列表、文件校验、归属校验、对象引用和解析交接；有 6 个相关单元测试及应用测试。 | `partial` | `required` | `docs/domain/domain-model.md`; `docs/contracts/api-contract.md`; `docs/architecture/backend-architecture.md` | `rewrite` | 资料上传已存在，但删除、批量操作和完整前端行为不在本轮后端资产裁决中。 | 后续 Gap Analysis 核对真实前端动作和当前 API 完整性。 |
| BE-CODE-PARSE-001 | code | `app/api/v1/document_parsing.py`; `app/services/{document_parsing,resume_parse_worker,resume_parse_finalization}_service.py`; `app/repositories/document_parsing_repository.py`; `app/schemas/document_parsing.py` | 简历画像查询、受控解析执行、结构化结果落库和终态处理；对应解析契约、Worker、Finalization 单元测试。 | `partial` | `required` | `docs/architecture/async-task-architecture.md`; `docs/contracts/async-task-contract.md`; `docs/integrations/external-capabilities.md` | `rewrite` | 外部解析测试被跳过，真实 MinerU/Qwen 运行证据不等同于单元测试通过。 | 后续 Slice 重新锁定 API/异步契约并补充真实能力证据。 |
| BE-CODE-ASYNC-001 | code | `app/infrastructure/tasks/{celery_app,dispatcher,worker}.py`; `app/services/async_task_execution_service.py`; `app/repositories/async_task_repository.py` | Celery、Dispatcher、任务运行记录、租约、执行权和有限重试相关实现；单元测试通过，但 Dispatcher/Repository 覆盖率明显低于整体覆盖率。 | `partial` | `conditional` | `docs/architecture/async-task-architecture.md`; `docs/contracts/async-task-contract.md` | `rewrite` | 测试通过不代表真实 Broker/Worker 拓扑、重投递和幂等已完成验证。 | 后续仅在解析或匹配 Slice 实际使用时确认能力范围。 |
| BE-CODE-STORAGE-001 | code | `app/infrastructure/storage/{local,cleanup}.py`; `app/repositories/object_storage_repository.py` | 本地受控对象存储、内容摘要、受控读取和清理实现；对象存储相关单元测试通过。 | `reusable` | `required` | `docs/architecture/backend-architecture.md`; `docs/integrations/external-capabilities.md` | `migrate` | 当前是本地对象存储，不代表已具备云对象存储或通用文件中心。 | 迁移时保留“本地 Demo 适配器”边界，不扩展为生产平台。 |
| BE-CODE-EXTERNAL-001 | code | `app/infrastructure/{mineru_mcp,mineru_mcp_client,qwen_profile}.py` | MinerU MCP、stdio 客户端和 Qwen 画像结构化适配器；对应 5 个适配器/客户端单元测试。 | `partial` | `conditional` | `docs/integrations/external-capabilities.md`; `docs/integrations/spikes/` | `reference` | 单元测试使用替身；真实外部验证测试当前被跳过，不能将适配器存在视为外部能力已通过。 | 后续按实际 Slice 建立专项 Spike 和 `passed/blocked/rejected` 结论。 |
| BE-CODE-API-001 | code | `app/api/router.py`; `app/api/dependencies/`; `app/api/v1/{auth,candidate_preparation,document_parsing,health}.py` | 当前公开路由包括认证、候选人资料、画像查询、健康检查和根路由；未发现岗位、匹配、投递、沟通业务路由。 | `partial` | `required` | `docs/contracts/api-contract.md` | `rewrite` | 现有 API 只覆盖后端已实现的前置能力，不能视为正式前端完整后端契约。 | 后续以正式 API Contract 和 Gap Analysis 为准补齐或废弃。 |
| BE-CODE-REPO-001 | code | `app/repositories/` | User、Candidate、Candidate Preparation、Document Parsing、Object Storage、Async Task 数据访问边界；代码未见 Service 直接持有 ORM Session 的主路径。 | `reusable` | `required` | `docs/architecture/backend-architecture.md`; `docs/development/backend-guidelines.md` | `migrate` | 当前 Repository 只覆盖已有实体，不能推导未来业务 Repository 已存在。 | 迁移职责规则，不复制当前实现细节。 |
| BE-CODE-MODEL-001 | code | `app/infrastructure/database/{base,models,session}.py` | 当前 SQLAlchemy 模型包括 User、Candidate、StoredFileObject、Resume、CandidateProfile、CandidateDocument、AsyncTaskRun。 | `partial` | `required` | `docs/domain/domain-model.md`; `docs/data/database-design.md` | `rewrite` | 未发现 Job、Job Description、Goal、Match、Application、Conversation、Message、Progress Event 等完整业务模型。 | 后续按 Slice 增量确认，不将旧全量模型文档直接视为已实现。 |
| BE-CODE-CORE-001 | code | `app/core/`; `app/main.py`; `app/infrastructure/runtime.py`; `app/infrastructure/cache/redis.py` | 配置、错误、异常、日志、请求上下文、健康检查和运行时依赖注入；对应配置、日志、边界和运行时测试。 | `reusable` | `required` | `docs/architecture/backend-architecture.md`; `docs/development/backend-guidelines.md` | `migrate` | 运行时可用性不等同于完整部署或生产观测能力。 | 迁移稳定分层和安全诊断边界。 |

## 3. 测试资产清单

最近一次 `uv run pytest` 结果：`139 passed, 9 skipped, 1 warning`；整体覆盖率 `80.63%`，达到 `pyproject.toml` 中 `80%` 门槛。该结果只证明当前测试集通过，不证明真实外部能力或未实现业务模块存在。

| Asset ID | 资产类别 | 原始路径 | 覆盖内容与证据 | 当前状态 | MVP 适用性 | 新事实源去向 | 处理动作 | 冲突或风险 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BE-TEST-UNIT-001 | test | `tests/unit/`（26 个测试文件） | 覆盖认证、身份、Schema、Repository、解析适配器、对象清理、异步基础设施、边界和公共组件；本地测试通过。 | `reusable` | `required` | `docs/development/backend-guidelines.md` | `reference` | 整体覆盖率达标，部分 Dispatcher、Repository 和 API 路径覆盖率偏低。 | 后续每个 Slice 只补当前路径的最小单元与契约测试。 |
| BE-TEST-INTEGRATION-001 | test | `tests/integration/`（2 个测试文件） | 覆盖应用和运行时依赖；本次测试结果中被跳过的依赖场景不构成真实拓扑通过证据。 | `partial` | `conditional` | `docs/architecture/async-task-architecture.md` | `reference` | 需要 Docker/数据库/Redis 环境的证据必须单独记录。 | 相关 Slice 阶段 8/9 再补真实集成证据。 |
| BE-TEST-EXTERNAL-001 | test | `tests/external/`（3 个测试文件） | MinerU、Qwen 和简历解析外部管线测试；本次结果包含跳过项，不能证明外部服务已通过。 | `pending` | `conditional` | `docs/integrations/spikes/` | `reference` | 外部凭证和服务可用性未在盘点阶段重新验证。 | 后续按外部能力专项验证规则处理。 |
| BE-TEST-FIXTURE-001 | test | `tests/fixtures/` | 受控简历和附加资料 PDF fixtures，仅作为测试输入，不迁移正文内容。 | `reusable` | `conditional` | `retain-history` | `retain` | 夹具可能含业务样本，不能进入文档正文、日志或追踪。 | 后续测试继续通过受控 fixtures 引用。 |

## 4. 数据库迁移与配置资产

### 4.1 Alembic 迁移链

| Asset ID | 资产类别 | 原始路径 | 资产摘要与当前证据 | 当前状态 | MVP 适用性 | 新事实源去向 | 处理动作 | 冲突或风险 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BE-MIG-001 | migration | `alembic/versions/20260723_0001_empty_baseline.py` | 初始空基线迁移。 | `reusable` | `required` | `docs/data/database-design.md` | `reference` | 仅表示迁移起点，不代表业务 Schema。 | 数据库设计文档引用迁移链，不复制历史脚本。 |
| BE-MIG-002 | migration | `alembic/versions/20260725_0002_auth_user_candidate.py` | User/Candidate 认证和身份表迁移。 | `reusable` | `required` | `docs/data/database-design.md`; `docs/domain/domain-model.md` | `reference` | 需要继续核对模型、迁移和 API 语义。 | 后续认证 Slice 作为已存在数据库事实复用。 |
| BE-MIG-003 | migration | `alembic/versions/20260727_0003_candidate_preparation.py` | 文件对象、简历、画像、附加资料及相关约束迁移。 | `reusable` | `required` | `docs/data/database-design.md`; `docs/domain/domain-model.md` | `reference` | 与旧全量 Data model 的业务范围不完全一致。 | 以实际迁移和 Model 为当前数据事实。 |
| BE-MIG-004 | migration | `alembic/versions/20260727_0004_async_dispatch_leases.py` | 异步 Dispatcher 租约和任务运行支撑迁移。 | `partial` | `conditional` | `docs/data/database-design.md`; `docs/contracts/async-task-contract.md` | `reference` | 迁移存在不等于真实投递、重投递和 Worker 行为已完成验证。 | 由解析/匹配 Slice 分别确认。 |
| BE-MIG-CHAIN-001 | migration | `careerpass-backend/alembic.ini`; `alembic/env.py`; `alembic/versions/` | 当前迁移按 `0001 → 0002 → 0003 → 0004` 形成单链；`tests/unit/test_alembic_baseline.py` 提供基础证据。 | `reusable` | `required` | `docs/data/database-design.md` | `migrate` | 未在本阶段执行迁移或修改 Schema。 | 后续数据库变更必须增量迁移并引用当前链。 |

### 4.2 根目录配置

| Asset ID | 资产类别 | 原始路径 | 资产摘要与当前证据 | 当前状态 | MVP 适用性 | 新事实源去向 | 处理动作 | 冲突或风险 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BE-CONFIG-001 | integration | `pyproject.toml`; `uv.lock`; `.python-version` | Python 3.12、FastAPI、SQLAlchemy、Alembic、Redis、Celery、MCP、pytest/ruff 依赖和测试门槛。 | `reusable` | `required` | `careerpass-backend/README.md`; `docs/architecture/backend-architecture.md` | `migrate` | 依赖版本和生产部署语义仍需在新基线中确认。 | 保留锁文件为实现事实，不在文档中复制全部依赖。 |
| BE-CONFIG-002 | integration | `Dockerfile`; `docker-compose.integration.yml`; `.env.example`; `alembic.ini` | 后端镜像、隔离 PostgreSQL/Redis/Worker/Dispatcher 拓扑、环境变量和迁移入口。 | `partial` | `conditional` | `careerpass-backend/README.md`; `docs/architecture/async-task-architecture.md` | `rewrite` | Compose 拓扑已被疑难问题案例验证可启动，但不等于业务闭环已通过。 | 新基线补充最小启动说明和验证边界。 |

## 5. 旧文档与契约资产

### 5.1 `.harness/wiki` 后端相关文档

| Asset ID | 原始路径 | 资产摘要 | 当前状态 | MVP 适用性 | 新事实源去向 | 处理动作 | 冲突或风险 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BE-DOC-MVP-001 | `.harness/wiki/01-governance/MVP scope and development boundaries.md` | 项目 MVP 用户、核心闭环、延期能力和不可降级约束。 | `partial` | `required` | `docs/product/backend-delivery-scope.md` | `rewrite` | 项目级范围与后端版本交付范围需要分层，不能整篇复制。 | 新基线阶段提取后端相关范围。 |
| BE-DOC-TECH-001 | `.harness/wiki/01-governance/Technical enablement and workflow governance.md` | 技术能力分层、Agent、RAG、异步和外部能力启用规则。 | `partial` | `conditional` | `docs/decisions/`; `docs/architecture/`; `docs/integrations/` | `rewrite` | 混合了项目治理和后端技术事实；需拆分静态事实与流程规则。 | 新基线明确各部分唯一归属。 |
| BE-DOC-DOMAIN-001 | `.harness/wiki/02-domain/Domain term.md` | 领域术语定义。 | `reusable` | `required` | `docs/domain/domain-model.md` | `migrate` | 术语本身稳定，但业务范围仍由新版本基线裁决。 | 迁移术语，不迁移未使用的未来实体。 |
| BE-DOC-DOMAIN-002 | `.harness/wiki/02-domain/Business model.md` | User、Candidate、Resume、Job、Match、Application、Conversation 等完整业务模型。 | `partial` | `required` | `docs/domain/domain-model.md` | `rewrite` | 文档范围明显大于当前代码实现；当前 Model 仅覆盖前置资料和异步实体。 | 以代码/迁移和 Slice 使用情况逐步确认实体。 |
| BE-DOC-RULES-001 | `.harness/wiki/02-domain/Business rules and state machines.md` | 业务规则和状态机集合。 | `partial` | `conditional` | `docs/product/business-rules.md`; `docs/domain/state-model.md` | `rewrite` | 规则包含尚未实现的投递、Agent、沟通和多阶段流程。 | 按 Slice 拆分，未实现规则保持 pending/deferred。 |
| BE-DOC-DATA-001 | `.harness/wiki/03-contracts/Data model.md` | 全量数据库表、字段、约束和实体关系说明。 | `partial` | `required` | `docs/data/database-design.md` | `rewrite` | 与当前四个迁移和 SQLAlchemy Model 不完全一致，包含尚未实现业务模型。 | 以实际迁移为事实，按 Slice 增量补充。 |
| BE-DOC-API-001 | `.harness/wiki/03-contracts/Interface protocol.md` | API 响应、接口和错误协议。 | `partial` | `required` | `docs/contracts/api-contract.md` | `rewrite` | 需要与实际路由和正式前端消费关系重新核对；首轮不将前端关系判定为已完成。 | 后续 Contract 阶段锁定 API 版本。 |
| BE-DOC-AGENT-001 | `.harness/wiki/04-technical-solutions/Agent workflow orchestration technical design.md` | Agent 规划、工作流注册、授权闸门和审计设计。 | `partial` | `conditional` | `docs/architecture/agent-workflow-architecture.md` | `rewrite` | 设计范围超出当前后端代码，不能作为已实现能力。 | 仅迁移稳定架构结论，Workflow 按 Slice 开发。 |
| BE-DOC-ASYNC-001 | `.harness/wiki/04-technical-solutions/Async task technical design.md` | Dispatcher、Worker、重试、租约和幂等设计。 | `partial` | `conditional` | `docs/architecture/async-task-architecture.md`; `docs/contracts/async-task-contract.md` | `rewrite` | 设计细节与当前测试/真实拓扑证据需要逐项对照。 | 以当前代码和实际验证记录拆分事实与目标。 |
| BE-DOC-STORAGE-001 | `.harness/wiki/04-technical-solutions/Object storage technical design.md` | 本地对象存储、去重、受控访问和清理机制。 | `partial` | `required` | `docs/architecture/backend-architecture.md`; `docs/integrations/external-capabilities.md` | `rewrite` | 当前实现是本地适配器，不应迁移为云存储或通用文件中心承诺。 | 保留已实现的本地边界。 |
| BE-DOC-PARSE-001 | `.harness/wiki/04-technical-solutions/Resume parsing technical design.md` | MinerU 文本提取、Qwen 结构化画像和失败映射。 | `partial` | `conditional` | `docs/integrations/`; `docs/contracts/async-task-contract.md` | `rewrite` | 外部服务真实证据与当前适配器能力需要区分。 | 后续解析 Slice 重新验证。 |
| BE-DOC-ENV-001 | `.harness/wiki/05-engineering/Development environment.md` | 本地开发、Compose、依赖服务和真实集成测试说明。 | `reusable` | `required` | `careerpass-backend/README.md`; `docs/architecture/async-task-architecture.md` | `reference` | 环境说明部分依赖当前用户机器，不应写入敏感路径或凭证。 | 迁移通用启动事实，保留案例到治理文档。 |

### 5.2 `.harness/contracts`

| Asset ID | 原始路径 | 资产摘要 | 当前状态 | MVP 适用性 | 新事实源去向 | 处理动作 | 冲突或风险 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BE-CONTRACT-001 | `.harness/contracts/registry.yaml`; `.harness/contracts/resume-parse-request-v1.yaml`; `.harness/contracts/JCG-2026-020-021-RESUME-PARSE-V1-joint-review.md` | `ResumeParseRequestV1` 已登记、锁定并有双方批准和 hash。 | `reusable` | `required` | `docs/contracts/async-task-contract.md` 或新专项契约 | `reference` | 契约仍绑定旧变更包路径；迁移后需要维护历史来源和新文档引用。 | 新 Contract 文档引用旧锁定证据，不静默修改版本。 |
| BE-CONTRACT-002 | `.harness/contracts/README.md` | 跨开发包契约登记和锁定规则。 | `partial` | `required` | `docs/decisions/backend-development-decisions.md`; `docs/contracts/` | `rewrite` | 项目治理规则与后端契约事实混合。 | 新基线拆分长期决策和具体契约。 |

### 5.3 `.harness/changes`

| Asset ID | 原始路径 | 资产摘要 | 当前状态 | MVP 适用性 | 新事实源去向 | 处理动作 | 冲突或风险 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BE-CHANGE-001 | `.harness/changes/in-progress/CHG-2026-009-*`; `CHG-2026-010-*` | 平台基础和认证用户初始化的进行中变更包，含设计、任务、测试和发布材料。 | `pending` | `required` | `retain-history` | `reference` | 变更包状态和后端当前代码需要核对，不能直接标记为完成。 | 新基线确认代码与历史包的关系。 |
| BE-CHANGE-002 | `.harness/changes/proposed/CHG-2026-011-*` 至 `CHG-2026-019-*` | 认证契约、业务规则、MVP 范围、异步模型、附件、画像和幂等等设计/契约变更。 | `partial` | `conditional` | `retain-history` | `archive` | 多数是设计意图或历史裁决，部分超出当前 Demo 后端实现。 | 后续只提取仍有效的事实。 |
| BE-CHANGE-003 | `.harness/changes/proposed/CHG-2026-020-*`; `CHG-2026-021-*` | 候选人资料准备和文档解析开发包，包含阶段台账、契约、方案、实现和验证记录。 | `partial` | `required` | `retain-history`; `docs/contracts/` | `reference` | 代码已经存在，但阶段状态、外部证据和新 Slice 归属仍需重新裁决。 | 作为解析/资料 Slice 的历史证据。 |
| BE-CHANGE-004 | `.harness/changes/ready/CHG-2026-001-*` 至 `CHG-2026-008-*` | 公司扁平化、数据一致性、过滤条件、匹配结果、附件、Schema、归属锚点和更新时间等 ready 变更。 | `pending` | `conditional` | `retain-history` | `archive` | `ready` 不等于已实现或当前必需；不能直接进入新数据库事实源。 | 只有被当前 Slice 证实时才提取。 |

## 6. 新后端占位文档

以下文件已创建但当前只有标题或占位内容，不构成设计事实：

| Asset ID | 路径 | 当前状态 | MVP 适用性 | 处理动作 |
| --- | --- | --- | --- | --- |
| BE-NEW-DOC-001 | `careerpass-backend/AGENTS.md`; `careerpass-backend/README.md` | `pending` | `required` | `rewrite` |
| BE-NEW-DOC-002 | `careerpass-backend/docs/decisions/` | `pending` | `required` | `rewrite` |
| BE-NEW-DOC-003 | `careerpass-backend/docs/product/` | `pending` | `required` | `rewrite` |
| BE-NEW-DOC-004 | `careerpass-backend/docs/contracts/` | `pending` | `required` | `rewrite` |
| BE-NEW-DOC-005 | `careerpass-backend/docs/architecture/` | `pending` | `required` | `rewrite` |
| BE-NEW-DOC-006 | `careerpass-backend/docs/domain/`; `docs/data/` | `pending` | `required` | `rewrite` |
| BE-NEW-DOC-007 | `careerpass-backend/docs/integrations/` | `pending` | `conditional` | `rewrite` |
| BE-NEW-DOC-008 | `careerpass-backend/docs/development/` | `pending` | `required` | `rewrite` |

这些占位文件不能被反向引用为已完成的全局事实源；迁移内容必须在新开发基线阶段逐份确认。

## 7. 冲突登记

| 冲突 ID | 参与资产 | 冲突内容 | 当前影响 | 后续裁决阶段 |
| --- | --- | --- | --- | --- |
| CONFLICT-001 | `app/api/v1/`、正式前端流程文档（后续映射） | 当前后端只发现认证、资料、解析和健康路由，正式产品流程还包含岗位、Agent、匹配、投递和沟通能力；前端关系本轮不裁决。 | 后续后端能力缺口范围未确定。 | Gap Analysis |
| CONFLICT-002 | `app/infrastructure/database/models.py`、`alembic/versions/`、`.harness/wiki/03-contracts/Data model.md` | 当前代码/迁移只覆盖 User、Candidate、文件/简历/画像、附加资料和异步任务；旧 Data model 还描述 Job、Match、Application、Conversation 等未在当前模型中发现的实体。 | 不得把旧全量数据模型直接迁移为当前数据库事实。 | 新基线 / Slice 方案 |
| CONFLICT-003 | `app/infrastructure/{mineru_mcp,qwen_profile}.py`、`tests/external/`、解析技术文档 | 适配器和单元测试存在，但外部测试本次被跳过，真实服务证据尚未在本盘点中确认。 | 外部能力状态不能标记为 `reusable`。 | 外部能力预验证 |
| CONFLICT-004 | `.harness/contracts/registry.yaml`、CHG-020/021、当前新目录 | `ResumeParseRequestV1` 已锁定，但契约仍以旧变更包为参与方和证据路径；新 Slice 归属尚未建立。 | 不能静默复制或修改已锁定契约。 | Contract 阶段 |
| CONFLICT-005 | `.harness/changes/*`、当前代码和测试 | 旧变更包存在 `proposed`、`ready`、`in-progress` 等状态；状态不等于当前实现完成或当前版本必需。 | 历史变更不能直接作为新 Slice 任务清单。 | 新基线 / Gap Analysis |

## 8. 待确认事项

| 待确认 ID | 事项 | 需要的证据 | 后续裁决阶段 | 当前处理 |
| --- | --- | --- | --- | --- |
| PENDING-001 | 当前正式前端的后端能力消费关系 | 前端 API 调用和流程映射 | Gap Analysis | 本轮不裁决 |
| PENDING-002 | User/Candidate 与 HR/求职者角色关系 | MVP 范围、认证契约和前端流程 | 新开发基线 / Contract | 保持 `pending` |
| PENDING-003 | 简历解析真实外部能力是否启用 | MinerU/Qwen 真实拓扑和受控样本证据 | 外部能力预验证 | 保持 `pending` |
| PENDING-004 | 异步 Dispatcher/Worker 的真实集成证据 | 隔离 Compose、任务终态、重复投递和幂等记录 | 解析或匹配 Slice | 保持 `pending` |
| PENDING-005 | 旧全量岗位、匹配、投递和沟通模型是否进入当前版本 | 前端映射和后端版本范围 | Gap Analysis / Slice 方案 | 保持 `pending` |
| PENDING-006 | 已锁定 `ResumeParseRequestV1` 在新文档体系中的引用位置 | Contract 注册表和参与包裁决 | Contract 阶段 | 保持原版本，不改写 |

## 9. 迁移阻塞清单

- 在 `backend-capability-map.md` 完成前，不能把旧全量业务模型和 Data model 迁移为当前后端必需事实。
- 在真实外部能力预验证前，不能把 MinerU/Qwen 适配器标记为已验证的可复用外部能力。
- 在 API/异步 Contract 重新确认前，不能把旧变更包中的字段和触发语义直接变成新 Slice 任务。
- 在认证角色和正式前端流程完成映射前，不能确定 HR 能力是否属于当前后端版本必需范围。
- 在 Job、Match、Application、Conversation 等实体被当前 Slice 证明需要前，不能提前创建或迁移其数据库设计。
- 旧 `.harness/changes` 只能作为历史证据，不能直接转换为新的 Vertical Slice 任务清单。

## 10. 盘点完成统计

| 资产类别 | 已盘点范围 | 当前结论 |
| --- | --- | --- |
| 后端代码 | `app/` 现有 API、Service、Repository、Schema、Model、Infrastructure 和任务能力组 | 认证/资料/存储/公共底座部分可复用；解析、异步、外部适配和业务 API 仍需重构或验证 |
| 测试 | 26 个 unit、2 个 integration、3 个 external 测试文件及 fixtures | `139 passed, 9 skipped`；覆盖率 `80.63%`；外部/真实拓扑证据仍不完整 |
| 数据库迁移 | 4 个 Alembic 版本及迁移配置 | 当前链覆盖认证、资料、异步租约；旧全量业务模型未被当前迁移证明 |
| 根目录配置 | Python/uv、Docker/Compose、环境模板、Alembic | 可作为开发基础事实，运行和生产边界需新基线重写 |
| 后端相关旧文档 | 12 个主要 `.harness/wiki` 文档 | 多数为 `partial`，需拆分项目治理、后端事实和延期设计 |
| 跨开发包契约 | `ResumeParseRequestV1` 注册、契约文件和联合评审记录 | 已锁定，可引用；新 Slice 归属待确认 |
| 变更包 | `CHG-2026-001` 至 `CHG-2026-021` 后端相关资产 | 以历史证据为主，不直接作为新事实源或任务清单 |
| 新后端文档 | `careerpass-backend/docs/` 当前占位文件 | 均为 `pending`，待新基线和后续 Slice 重写 |

## 11. 盘点边界声明

- 本清单不迁移、删除或覆盖任何旧资产。
- 本清单不裁决正式前端的实际 API 消费关系；该事项留给后续能力映射和 Gap Analysis。
- 本清单不修改业务范围、API 语义、数据模型、状态机或外部能力选型。
- 本清单不记录凭证、简历原文、模型原始响应、绝对内部路径或其他敏感原值。
- “可复用”只表示当前资产具备迁移或引用证据，不表示它已经满足下一个 Slice 的完整验收。
