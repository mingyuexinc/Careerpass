# 测试报告

## 执行日期

2026-07-22

## 执行命令与结果

| 命令 | 结果 | 覆盖范围 |
| --- | --- | --- |
| `python .harness/changes/tools/validate_changes.py` | 通过 | 变更目录命名、全局编号唯一性、状态一致性及必填文件。 |
| `git diff --check -- .harness/rules/Coding specification.md .harness/changes/in-progress/CHG-2026-009-platform-foundation` | 通过 | 文档变更的空白字符错误。 |
| `rg -n 'msg|message' .harness/rules/Coding specification.md .harness/wiki/Interface protocol.md` | 通过 | 编码规范与接口协议均以 `msg` 表达响应描述字段，未发现 `message` 作为响应字段契约。 |
| `uv run pytest` | 通过：11 passed | L1 配置校验、响应信封、应用工厂、404/409/500 异常映射，以及未知异常内容不进入响应或日志。 |
| `uv run pytest`（L2） | 通过：17 passed | 请求 ID 透传/替换、请求上下文、响应头、脱敏、日志 JSON 白名单、第三方日志过滤及 L1 回归。 |
| `python ..\\.harness\\changes\\tools\\validate_changes.py` | 通过 | L2 文档更新后的变更包结构与状态一致性。 |
| `git diff --check` | 通过 | L2 源码与文档变更无空白错误。 |
| `uv run pytest`（L3） | 通过：24 passed | PostgreSQL 异步引擎、会话工厂、幂等释放、空元数据、架构边界、Alembic revision 图和无 DDL 基线，以及 L1/L2 回归。 |
| `uv run pytest`（L4） | 通过：32 passed | Redis 生命周期、Celery JSON/状态/重试配置、探针输入校验、Redis 超时降级、健康检查成功/503 契约，以及 L1-L3 回归。 |
| `uv run ruff check .`（L5） | 通过 | E/F/I 静态检查与导入顺序。 |
| `uv run pytest`（L5） | 通过：38 passed, 1 skipped | 默认质量门禁；覆盖率阈值 >=80%，应用代码实际 100%。跳过项是需 Compose 真实依赖的集成测试。 |

## 未解决风险

- 默认质量门禁已通过；真实 PostgreSQL/Redis/Celery Worker 的联通性、Alembic `upgrade head` 演练、发布回滚与观测尚未在本机完成，因为未发现可用的 Docker CLI。CI 工作流会执行该集成门禁。第三方 FastAPI/Starlette TestClient 仍有一条弃用警告，不影响测试结果。
- 健康检查的 HTTP 503 与信封 `code: 500` 的映射已被记录，须在 L4 测试中验证。
