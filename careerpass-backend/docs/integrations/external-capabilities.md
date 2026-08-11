# 外部能力总览

> 本文档记录当前代码已经接入或明确配置的外部能力及其证据边界，不定义单个 Slice 的业务流程。

| 能力 | 当前用途 | 实现证据 | 真实验证状态 |
| --- | --- | --- | --- |
| PostgreSQL 16 | 业务数据和异步任务权威状态 | SQLAlchemy、Alembic、Repository | 集成环境可验证；具体 Slice 仍需引用验证结果 |
| Redis 7.4 | Celery Broker 和就绪依赖 | Redis 运行时、Celery 配置 | Compose 连通不等于任务闭环通过 |
| MinerU MCP | 正式简历文本提取 | stdio/HTTP Client 与适配器单元测试 | partial；工具发现已验证，受控文件完整解析证据待确认 |
| Qwen Plus | 结构化候选人画像 | Qwen 适配器和 Schema 单元测试 | partial；真实模型调用由外部测试显式启用 |

## 1. 通用边界

- 外部能力只在当前 Slice 关键路径实际需要时启用。
- 配置存在、适配器代码、Mock 或单元测试不构成真实服务通过证据。
- 凭证只从 Settings/SecretStr 和运行环境读取，不进入 API、任务契约、日志或追踪。
- 外部输出必须经过结构化和业务校验，供应商原始错误映射为受控失败分类。
- 新供应商、传输方式或关键参数必须在 Readiness Check 前完成最小真实验证。

## 2. 非外部能力

当前本地对象存储属于后端 Infrastructure，不作为第三方外部能力；其边界见后端总体架构。
