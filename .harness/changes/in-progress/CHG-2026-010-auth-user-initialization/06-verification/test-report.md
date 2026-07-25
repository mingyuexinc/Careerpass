# 真实集成测试报告

## 结果

- 状态：通过
- 执行日期：2026-07-25
- 命令：`uv run pytest -m integration`
- 结果：`1 passed, 78 deselected`
- 覆盖率：84.08%，满足不低于 80% 的门槛。

## 验证链路

1. Alembic 可重复升级至 `head`，并验证 `users`、`candidates` 表及更新时间触发器。
2. Repository 在真实数据库中原子创建 `User + Candidate`，并完成身份重新解析。
3. FastAPI 在真实 PostgreSQL/Redis 依赖下验证注册、重复注册冲突、登录、`/auth/me` 与 `/health/ready`。

测试中出现 Starlette 对 `httpx`/`TestClient` 的弃用警告，不影响本次结论；后续依赖升级时处理。
