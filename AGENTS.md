# 职达Agent

## 文档分层与项目入口

本项目的文档按“AI 如何开发、项目从哪里进入、子工程应该是什么”分层：

| 文档层 | 回答的问题 | 典型内容 |
| --- | --- | --- |
| `.harness/` | AI 怎样开发？ | AI Coding 工作流和可复用 Skill |
| 根 `AGENTS.md` | 整个项目从哪里进入？ | 项目导航、子工程入口和跨工程红线 |
| `careerpass-frontend/AGENTS.md` | 前端开发先看什么？ | 前端约束和前端文档导航 |
| `careerpass-backend/AGENTS.md` | 后端开发先看什么？ | 后端约束和后端事实源导航 |
| `careerpass-frontend/docs/` | 前端应该是什么？ | 页面、用户流程、UI、架构、组件和交互 |
| `careerpass-backend/docs/` | 后端应该是什么？ | 领域、接口、数据库、工作流和垂直切片（Vertical Slice） |
| `careerpass-frontend/src/`、`careerpass-backend/app/` | 现在实际是什么？ | 当前正式实现 |

文档层职责不能相互替代：`.harness/` 的执行规则不能直接作为后端业务事实，前端页面不能单独决定后端领域规则，后端文档也不能替代当前源代码的实现证据。

项目入口阅读顺序：先阅读本文件，再按任务进入 `careerpass-frontend/AGENTS.md` 或 `careerpass-backend/AGENTS.md`；进入子工程后，以对应 `docs/` 中的事实源为准。

后端疑难问题入口：凡涉及后端环境、依赖、数据库、Docker、架构、联调或故障排查，进入后端任务后必须优先阅读 [`careerpass-backend/docs/development/backend-troubleshooting.md`](careerpass-backend/docs/development/backend-troubleshooting.md)，并先复用其中适用的诊断路径；问题解决后将可复用结论补充回该文档。

## 文档内容生成精简规则

适用于项目内所有新建、修订和评审文档：

- 以最小充分内容为目标，不以篇幅或解释完整度为质量标准。
- 一个规则、结论或事实只定义一次；已有事实源只引用路径，不重复转述。
- 严格遵守文档分层：上游文档负责定义，下游文档负责引用和应用，具体 Slice 文档负责细化。
- 修改文档时先删除重复、越界和过程性内容，再补充本文件职责范围内的缺失事实。
- 章节只保留本文件必须回答的问题；不主动增加背景、展望、重复总结或装饰性章节。
- 表格只保留当前文档实际使用的字段，不把下游 Contract、数据、权限、状态或实现细节提前复制进来。
- 未明确要求时，优先使用短章节、短表格和单句结论；需要展开时引用事实源而不是重新解释。
- 文档说明文字优先使用中文；仅保留必要的专有名词、技术名称、代码标识、API 路径、状态值和阶段名称，首次出现的非中文术语应给出中文含义。
- 完成文档后必须进行一次去重检查，删除重复规则、重复结论、重复表格和可合并段落。

## 技术栈

|   层级   |   技术   |
| - - - - -| - - - - -|
|   前端   |   …     |
|   后端   |  FastAPI 0.139.x  + Pydantic 2.x + SQLAlchemy 2.0.x + Alembic 1.x + PostgreSQL 16.x + Redis 7.4.x + Celery 5.6.x |
| 大模型 | LangChain 1.1.x + LangSmith +  Qwen Plus API + Pinecone 9.1.x + text-embedding-v4 + qwen3-rerank |



## 红线（不可违反）

1. **开发必须按前端优先、Slice 层级的六阶段门禁执行**：依次通过 Slice Select、Slice Design、Readiness Check、Implement、Verify 和 Close；当前 Gate 未通过不得进入下一阶段。任何 Slice 边界、授权、数据模型、状态机、契约或关键依赖变化，必须按影响回退并重新通过相应 Gate。
1. **数据访问必须经过 Repository 层**：禁止在 Service、Agent、Workflow 中直接编写 SQL 或访问 ORM Session；禁止反向跨层依赖。
1. **所有资源必须进行候选人/用户级权限与归属校验**：简历、画像、求职目标、匹配结果、投递记录、会话和消息，均不得仅凭资源 ID 读取或修改，必须校验当前用户的归属关系。
1. **LLM 输出不可直接作为事实或执行指令**：必须经 Pydantic 结构化校验、业务规则校验后才可入库或驱动流程；涉及投递、对外沟通、状态变更等副作用操作，必须有明确授权与可审计记录。
1. **异步任务必须可重试、幂等且状态可追踪**：简历解析、Embedding、索引、匹配等 Celery 任务必须记录任务状态和失败原因；重试不得产生重复数据、重复投递或重复外发消息。
1. **业务状态变更必须受状态机/合法迁移约束并记录事件**：例如投递状态变化必须校验前置状态，并写入 `Progress Event`；禁止绕过业务流程直接更新状态字段。
1. **敏感原值与安全凭证不得暴露，诊断信息必须脱敏且最小化**：密码、密码哈希、令牌、未经脱敏的简历原文、联系方式、完整内部文件定位、模型原始响应及含敏感内容的异常堆栈，不得进入日志、LangSmith 追踪或非必要接口响应；不得进入 Prompt 的内容也不得超出任务所需的已脱敏数据。日志与 LangSmith 追踪仅记录用于定位问题的最小脱敏诊断信息，例如关联 ID、处理阶段、状态、失败分类、耗时和重试次数。****
1. **Agent 的工具调用必须有边界**：工具输入须校验，外部调用须设置超时、重试和错误处理；禁止让模型拼接 SQL、Shell 命令或未经校验的外部请求。
1. **API 响应必须遵循统一格式 ** - `{code、msg、data}`结构
1. **疑难问题必须先查案例**：遇到后端环境、依赖、架构、联调或故障排查类疑难问题，先查询 `careerpass-backend/docs/development/backend-troubleshooting.md`；已有案例适用时优先复用其诊断路径，问题解决后将可复用结论补充回该文档。



## 文件索引

|   文件   |   用途   |
| - - - - -| - - - - - |
| `.harness/README.md` | AI Coding 指令范围和阅读顺序 |
| `.harness/rules/AI coding workflow.md` | 前端优先、Slice 层级的 AI Coding Gate |
| `.harness/skills/slice-design/SKILL.md` | Slice 选择、设计和 Readiness 文档技能 |
| `archive/` | 旧开发包和契约历史归档，不属于当前事实源 |

## 子工程入口

| 子工程 | 入口文档 | 事实源目录 |
| --- | --- | --- |
| 前端 | [`careerpass-frontend/AGENTS.md`](careerpass-frontend/AGENTS.md) | [`careerpass-frontend/docs/`](careerpass-frontend/docs/) |
| 后端 | [`careerpass-backend/AGENTS.md`](careerpass-backend/AGENTS.md) | [`careerpass-backend/docs/`](careerpass-backend/docs/) |

进入具体子工程后，先阅读对应入口文档；不要用根项目治理文档替代子工程的产品、架构、接口或数据事实源。
