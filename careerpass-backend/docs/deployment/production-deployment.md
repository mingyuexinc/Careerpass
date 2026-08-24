# 生产部署操作

生产部署使用仓库根目录的 `docker-compose.production.yml`，配置文件位于本目录下未提交的 `.env.production`。

## 首次准备

```sh
cp .env.production.example .env.production
chmod 600 .env.production
```

填写域名、PostgreSQL、JWT、生产账号和 MinerU/Qwen 凭证。真实值不得提交仓库。

## 启动顺序

从 `careerpass-backend` 目录执行：

```sh
docker compose --env-file .env.production -f ../docker-compose.production.yml config --quiet
docker compose --env-file .env.production -f ../docker-compose.production.yml up -d postgres redis
docker compose --env-file .env.production -f ../docker-compose.production.yml --profile ops run --rm migrate
docker compose --env-file .env.production -f ../docker-compose.production.yml up -d backend worker dispatcher web
docker compose --env-file .env.production -f ../docker-compose.production.yml ps
```

生产环境只有 `web` 映射 80/443；PostgreSQL、Redis 和 Backend 只在内部网络可达。

## 发布前备份

```sh
./scripts/backup-production.sh
```

脚本会生成 PostgreSQL 逻辑备份、对象文件归档和校验清单。迁移前和正式发布前都必须执行。生成的备份应下载到服务器之外的存储位置；同一台服务器上的副本不能作为完整灾备。

轻量应用服务器快照用于服务器级回滚。创建快照前应完成数据库逻辑备份，避免只依赖磁盘快照恢复业务数据。

## 健康检查

```sh
curl --fail https://<domain>/health/live
curl --fail https://<domain>/health/ready
docker compose --env-file .env.production -f ../docker-compose.production.yml ps
```

`/health/ready` 通过只表示 Backend 能访问 PostgreSQL、Redis 并完成本地配置检查；Worker 还必须通过容器状态和实际任务终态单独验证。

## 回滚边界

- 镜像问题：恢复上一版本镜像并重新启动业务服务。
- 迁移问题：先保留现场，使用备份在隔离环境验证恢复，不直接删除生产卷。
- 数据盘问题：通过轻量服务器快照回滚，并使用 PostgreSQL/对象文件备份核对业务一致性。
