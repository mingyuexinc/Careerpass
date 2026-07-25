# 职达Agent

## 技术栈

|   层级   |   技术   |
| - - - - -| - - - - -|
|   前端   |   …     |
|   后端   |  FastAPI 0.139.x  + Pydantic 2.x + SQLAlchemy 2.0.x + Alembic 1.x + PostgreSQL 16.x + Redis 7.4.x + Celery 5.6.x |
| 大模型 | LangChain 1.1.x + LangSmith +  Qwen Plus API + Pinecone 9.1.x + text-embedding-v4 + qwen3-rerank |



## 红线（不可违反）

1. **数据访问必须经过 Repository 层**：禁止在 Service、Agent、Workflow 中直接编写 SQL 或访问 ORM Session；禁止反向跨层依赖。
1. **所有资源必须进行候选人/用户级权限与归属校验**：简历、画像、求职目标、匹配结果、投递记录、会话和消息，均不得仅凭资源 ID 读取或修改，必须校验当前用户的归属关系。
1. **LLM 输出不可直接作为事实或执行指令**：必须经 Pydantic 结构化校验、业务规则校验后才可入库或驱动流程；涉及投递、对外沟通、状态变更等副作用操作，必须有明确授权与可审计记录。
1. **异步任务必须可重试、幂等且状态可追踪**：文档解析、Embedding、索引、匹配等 Celery 任务必须记录任务状态和失败原因；重试不得产生重复数据、重复投递或重复外发消息。
1. **业务状态变更必须受状态机/合法迁移约束并记录事件**：例如投递状态变化必须校验前置状态，并写入 `Progress Event`；禁止绕过业务流程直接更新状态字段。
1. **敏感信息不得进入日志、Prompt、追踪平台或接口响应**：包括密码哈希、令牌、简历原文、联系方式及其他个人隐私。日志与 LangSmith 追踪应做脱敏，并遵守最小必要原则。****
1. **Agent 的工具调用必须有边界**：工具输入须校验，外部调用须设置超时、重试和错误处理；禁止让模型拼接 SQL、Shell 命令或未经校验的外部请求。
1. **API 响应必须遵循统一格式 ** - `{code、msg、data}`结构



## 文件索引

|   文件   |   用途   |
| - - - - -| - - - - - |
|   `.harness/rules/Engineering structure.md`   | 项目目录结构规范     |
|   `.harness/rules/Coding specification.md`   | 编码标准与约定     |
|  `.harness/rules/Development process specification.md`   | 开发流水线与流程 |    
|   `.harness/skills/coding-skill/SKILL.md`   | 编码实现技能     |
|   `.harness/skills/expert-reviewer/SKILL.md`   | 专家评审技能     |
|   `.harness/wiki/Business model.md`   | 业务模型与实体关系    |
|   `.harness/wiki/Business rules and state machines.md`   | 模块业务规则、状态机、合法迁移与操作前置条件    |
|   `.harness/wiki/MVP scope and development boundaries.md`   | MVP 开发范围、延期能力与不可降级约束；每次需求开发前的范围裁决基准    |
|   `.harness/wiki/Interface protocol.md`   | API接口协议定义    |
|   `.harness/wiki/Data model.md`   | 数据库Schema与表定义   |
|   `.harness/wiki/Development environment.md`   | 本地开发、Docker Compose 依赖服务、环境变量与真实集成测试说明   |
|   `.harness/changes/`   | 变更追踪目录   |
