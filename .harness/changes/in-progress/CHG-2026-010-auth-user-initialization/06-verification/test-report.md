# 真实集成测试报告

## 结果

- 状态：通过
- 执行日期：2026-07-25
- 命令：`uv run pytest -m integration`
- 结果：`1 passed, 78 deselected`
- 覆盖率：84.08%，满足不低于 80% 的门槛。

## 密码契约修复复验

- 执行日期：2026-07-31
- 针对性命令：`uv run pytest --no-cov tests/unit/test_auth_schemas.py tests/unit/test_registration_service.py tests/unit/test_login_service.py tests/integration/test_application.py`
- 结果：`32 passed`
- 全量命令：`uv run pytest`
- 结果：`132 passed, 9 skipped`
- 全量覆盖率：`81.38%`，达到不低于 80% 的门槛。
- 静态检查：`uv run ruff check app tests alembic`，通过。

## 验证链路

1. Alembic 可重复升级至 `head`，并验证 `users`、`candidates` 表及更新时间触发器。
2. Repository 在真实数据库中原子创建 `User + Candidate`，并完成身份重新解析。
3. FastAPI 在真实 PostgreSQL 依赖下验证注册、重复注册冲突、登录、`/auth/me` 与 `/health/ready`。
4. 契约测试验证非空短密码、字母/数字/特殊字符单一组成密码均可通过；空密码和超过 128 字符密码被拒绝，密码不会出现在模型表示中。

> 历史执行环境同时包含 Redis，但 Redis 认证限流已于 2026-07-31 移出本模块；其相关结果不再属于当前认证模块验收范围。PostgreSQL 阶段 2 预验证的现行证据见 `02-prevalidation/postgresql-prevalidation.md`。

测试中出现 Starlette 对 `httpx`/`TestClient` 的弃用警告，不影响本次结论；后续依赖升级时处理。
