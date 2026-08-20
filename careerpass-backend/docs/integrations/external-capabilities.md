# 外部能力总览

> 本文档记录当前代码已经接入或明确配置的外部能力及其证据边界，不定义单个 Slice 的业务流程。

| 能力 | 当前用途 | 实现证据 | 真实验证状态 |
| --- | --- | --- | --- |
| PostgreSQL 16 | 业务数据和异步任务权威状态 | SQLAlchemy、Alembic、Repository | 集成环境可验证；具体 Slice 仍需引用验证结果 |
| Redis 7.4 | Celery Broker 和就绪依赖 | Redis 运行时、Celery 配置 | Compose 连通不等于任务闭环通过 |
| MinerU MCP | 正式简历文本提取 | stdio/HTTP Client 与适配器单元测试 | partial；工具发现已验证，受控文件完整解析证据待确认 |
| Qwen Plus | 结构化候选人画像 | Qwen 适配器和 Schema 单元测试 | partial；真实模型调用由外部测试显式启用 |
| Qwen Plus（S10-01） | 基于 Resume-derived 结构化事实生成受约束沟通回复 | `qwen_communication.py`、Pydantic 输出 Schema、S10 Readiness/Verify/Close 记录 | passed；2026-08-20 已完成脱敏结构化事实最小真实调用、有限失败分类、经历范围内否定回答和真实前端回答复验；固定 Fixture 验收不依赖外部模型 |

S10-02 不新增大模型或第三方能力，文件名匹配采用确定性标准化、关键词和受控别名；附件下载复用现有 CandidateDocument/对象存储基础设施。2026-08-20 已通过迁移 `20260820_0016`、PostgreSQL/本地对象存储联调，验证对象下载、7 天独立有效期、CandidateDocument 删除后的附件交接和过期清理引用保护。

## 1. 通用边界

- 外部能力只在当前 Slice 关键路径实际需要时启用。
- 配置存在、适配器代码、Mock 或单元测试不构成真实服务通过证据。
- 凭证只从 Settings/SecretStr 和运行环境读取，不进入 API、任务契约、日志或追踪。
- 外部输出必须经过结构化和业务校验，供应商原始错误映射为受控失败分类。
- 新供应商、传输方式或关键参数必须在 Readiness Check 前完成最小真实验证。

## 2. 非外部能力

当前本地对象存储属于后端 Infrastructure，不作为第三方外部能力；其边界见后端总体架构。
