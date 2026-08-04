# 职达Agent

## 技术栈

|   层级   |   技术   |
| - - - - -| - - - - -|
|   前端   |   …     |
|   后端   |  FastAPI 0.139.x  + Pydantic 2.x + SQLAlchemy 2.0.x + Alembic 1.x + PostgreSQL 16.x + Redis 7.4.x + Celery 5.6.x |
| 大模型 | LangChain 1.1.x + LangSmith +  Qwen Plus API + Pinecone 9.1.x + text-embedding-v4 + qwen3-rerank |



## 红线（不可违反）

1. **模块开发必须按十一阶段串行门禁执行**：未完成需求分析门禁，不得开展技术预验证、方案设计、任务拆分或编码；未完成任一阶段门禁，不得开启下一阶段。任何范围、授权、数据模型、状态机或关键依赖变化，必须按影响回退并重新通过相应门禁。
1. **数据访问必须经过 Repository 层**：禁止在 Service、Agent、Workflow 中直接编写 SQL 或访问 ORM Session；禁止反向跨层依赖。
1. **所有资源必须进行候选人/用户级权限与归属校验**：简历、画像、求职目标、匹配结果、投递记录、会话和消息，均不得仅凭资源 ID 读取或修改，必须校验当前用户的归属关系。
1. **LLM 输出不可直接作为事实或执行指令**：必须经 Pydantic 结构化校验、业务规则校验后才可入库或驱动流程；涉及投递、对外沟通、状态变更等副作用操作，必须有明确授权与可审计记录。
1. **异步任务必须可重试、幂等且状态可追踪**：简历解析、Embedding、索引、匹配等 Celery 任务必须记录任务状态和失败原因；重试不得产生重复数据、重复投递或重复外发消息。
1. **业务状态变更必须受状态机/合法迁移约束并记录事件**：例如投递状态变化必须校验前置状态，并写入 `Progress Event`；禁止绕过业务流程直接更新状态字段。
1. **敏感原值与安全凭证不得暴露，诊断信息必须脱敏且最小化**：密码、密码哈希、令牌、未经脱敏的简历原文、联系方式、完整内部文件定位、模型原始响应及含敏感内容的异常堆栈，不得进入日志、LangSmith 追踪或非必要接口响应；不得进入 Prompt 的内容也不得超出任务所需的已脱敏数据。日志与 LangSmith 追踪仅记录用于定位问题的最小脱敏诊断信息，例如关联 ID、处理阶段、状态、失败分类、耗时和重试次数。****
1. **Agent 的工具调用必须有边界**：工具输入须校验，外部调用须设置超时、重试和错误处理；禁止让模型拼接 SQL、Shell 命令或未经校验的外部请求。
1. **API 响应必须遵循统一格式 ** - `{code、msg、data}`结构
1. **疑难问题必须先查案例**：遇到环境、依赖、架构、联调或故障排查类疑难问题，先查询 `.harness/wiki/00-governance/Difficult problem summary.md`；已有案例适用时优先复用其诊断路径，问题解决后将可复用结论补充回该文档。



## 文件索引

|   文件   |   用途   |
| - - - - -| - - - - - |
|   `.harness/rules/Engineering structure.md`   | 项目目录结构规范     |
|   `.harness/rules/Coding specification.md`   | 编码标准与约定     |
|  `.harness/rules/Development process specification.md`   | 开发流水线与流程 |    
|   `.harness/skills/coding-skill/SKILL.md`   | 编码实现技能     |
|   `.harness/skills/expert-reviewer/SKILL.md`   | 专家评审技能     |
|   `.harness/wiki/00-governance/Difficult problem summary.md`   | 疑难问题案例、诊断路径、解决方案与验证边界；遇到疑难问题时必须先查询    |
|   `.harness/wiki/01-governance/MVP scope and development boundaries.md`   | MVP 开发范围、延期能力与不可降级约束；每次需求开发前的范围裁决基准    |
|   `.harness/wiki/01-governance/Technical enablement and workflow governance.md`   | 技术能力分层、Agent 工作流治理与 RAG 启用条件；涉及 Agent、Workflow、RAG、异步任务时必读    |
|   `.harness/wiki/02-domain/Domain term.md`   | 领域术语与统一定义    |
|   `.harness/wiki/02-domain/Business model.md`   | 业务模型与实体关系    |
|   `.harness/wiki/02-domain/Business rules and state machines.md`   | 模块业务规则、状态机、合法迁移与操作前置条件    |
|   `.harness/wiki/03-contracts/Interface protocol.md`   | API接口协议定义    |
|   `.harness/wiki/03-contracts/Data model.md`   | 数据库Schema与表定义   |
|   `.harness/wiki/04-technical-solutions/Agent workflow orchestration technical design.md`   | Agent 规划、工作流注册、编排状态、授权闸门与审计；涉及 Agent 工作流时必读   |
|   `.harness/wiki/04-technical-solutions/Async task technical design.md`   | 异步任务的可靠入队、Dispatcher、重试、超时与运行治理；涉及 Redis、Celery、异步任务时必读   |
|   `.harness/wiki/04-technical-solutions/Object storage technical design.md`   | 本地对象存储、去重、受控读取与清理机制；涉及文件上传或读取时必读   |
|   `.harness/wiki/04-technical-solutions/Resume parsing technical design.md`   | 正式简历的 MinerU MCP 文本提取、画像 Schema、失败映射与验收；涉及简历解析时必读   |
|   `.harness/wiki/05-engineering/Development environment.md`   | 本地开发、Docker Compose 依赖服务、环境变量与真实集成测试说明   |
|   `.harness/changes/`   | 变更追踪目录   |
