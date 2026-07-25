# T07 本地 Compose 预发等价验证记录

## 适用范围与结论

- 执行日期：2026-07-25
- 环境：本机 Docker Compose 隔离环境，作为预发等价验证；不是远程 staging 或生产发布。
- 结论：通过。
- 保留状态：变更包仍为 `in-progress`，等待人工发布审批与真实目标环境发布。

## 环境与依赖检查

| 项目 | 结果 |
| --- | --- |
| PostgreSQL 16 | healthy，`54329 -> 5432` 宿主机映射可用 |
| Redis 7.4 | healthy，`63790 -> 6379` 宿主机映射可用 |
| Alembic | 在 Backend 容器中执行 `alembic upgrade head` 成功，可安全重复执行 |
| Backend | Compose 构建并启动，`8080 -> 8080` 映射可用 |
| Celery Worker | Compose 构建并启动，依赖 PostgreSQL/Redis 健康后运行 |

## HTTP 冒烟结果

| 场景 | 结果 |
| --- | --- |
| `GET /health/live` | `200` |
| `GET /health/ready` | `200` |
| 注册隔离测试账号 | `200`，返回必要 Access Token |
| 登录隔离测试账号 | `200` |
| 使用登录 Token 调用 `/api/v1/auth/me` | `200`，返回用户名与注册账号一致 |
| Redis 限流 | 前九次失败登录返回 `401`，第十次返回 `429` |

测试过程未在记录中保存 Token、密码、完整连接串或用户标识。测试数据只存在于隔离 Compose 数据库。
