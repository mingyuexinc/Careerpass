# 发布与回滚计划

## 发布前置条件

- 人工发布审批已获得，且目标环境使用独立于本地 Compose 的密钥与数据库凭据。
- `JWT_SECRET_KEY` 长度不少于 32 字符；`APP_ENV=production`、`DEBUG=false`。
- PostgreSQL 连接信息已在受控配置中设置；不将密钥、Token 或完整连接串写入发布记录。Redis 与 Celery 如被其他模块启用，应由其所属变更包单独验证。
- `uv run ruff check app tests alembic`、`uv run pytest` 和真实依赖集成测试均已通过。
- Alembic 正向迁移、回滚脚本与恢复负责人已确认；未审批前不得执行破坏性回滚。

## 发布步骤

1. 构建并部署锁定 `uv.lock` 的 Backend 候选镜像。
2. 在目标数据库执行 `alembic upgrade head`；确认目标 revision 与预期一致。
3. 启动 Backend，确认进程未输出密码、JWT 或连接字符串。
4. 调用 `/health/live`、`/health/ready`；就绪检查必须返回 `200`。
5. 使用隔离测试账号验证注册、登录和 `/api/v1/auth/me`；不在发布记录保存 Access Token。
6. 在观察窗口内查看 5xx、401 与就绪检查失败率；不得记录用户凭据或 Token。

## 回滚步骤

1. 若迁移、启动或认证冒烟失败，停止新增版本流量并恢复上一稳定 Backend/Worker 镜像与受控配置。
2. 若本次新增的 `users`/`candidates` 尚未承载需要保留的业务数据，可经审批使用 `04-data/rollback.sql` 或对应 Alembic downgrade 按依赖反向顺序回滚；否则仅回滚应用，保留 Schema 并制定数据迁移方案。
3. 恢复后再次检查 `/health/live`、`/health/ready` 与受保护接口，确认没有残留异常流量。
4. 记录不含敏感信息的故障时间线、影响范围、执行人和最终数据库 revision。
