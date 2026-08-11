# 后端故障排查

> 本文档记录可复用的后端环境、依赖和联调诊断案例。只保留必要的脱敏诊断信息。

## 使用规则

1. 先确认问题属于环境、依赖、架构还是业务实现。
2. 优先执行只读检查，不修改共享或生产环境。
3. 复用案例时重新验证当前机器和当前配置，不直接套用历史结论。
4. 新案例只记录原因、诊断路径、解决方法、验证边界和必要的关联文件。

## Docker CLI 或 Docker Engine 不可用导致隔离 Compose 无法启动

### 现象与原因

当前终端找不到 `docker`，或 Docker Engine 尚未运行。该问题不表示 Compose、PostgreSQL、Redis 或 Celery 配置错误；必须先恢复 Docker CLI/Engine，才能执行本项目的真实数据库和联调验证。

### 诊断

1. 检查 docker 和 docker compose 是否可发现。
2. 检查 Docker Desktop 进程和 Engine 状态。
3. 如 CLI 已安装但 PATH 未刷新，使用已确认的 CLI 绝对路径验证 docker version。
4. Engine 可用后启动 docker-compose.integration.yml，并检查 PostgreSQL、Redis、Dispatcher 和 Worker。
5. 查看 Worker 日志，确认连接 Broker 和注册 careerpass.resume_parse。

### 解决与验证边界

- 安装或启动 Docker Desktop，并在新终端刷新 PATH；若 CLI 已安装，使用已确认的绝对路径执行 `docker version`。
- 只启动本项目隔离 Compose，不触碰共享环境。
- 本项目 Compose 会先运行 `migrate` 服务执行 `alembic upgrade head`，再启动 Backend、Worker 和 Dispatcher；Backend 启动时还会幂等写入两个受控演示账号。
- PostgreSQL/Redis healthy、Worker ready 只证明运行拓扑可用；任务终态、重试、租约、重投递和幂等仍需单独验证。
- 诊断输出不得包含 API Key、数据库密码、JWT、简历正文、对象路径或模型原始响应。

## Docker CLI 文件存在但当前执行上下文拒绝运行

### 现象与原因

Docker Desktop 和 CLI 文件存在，PATH 也包含 Docker 目录，但当前 Shell 或受限执行上下文运行 `docker.exe` 返回“拒绝访问”。这与 Docker Engine 未启动不同，也不表示项目 Compose 配置错误。

### 诊断与处理

1. 用 `Get-Command docker`、`Test-Path` 和已确认的绝对路径分别检查命令发现、文件存在性和 CLI 文件位置。
2. 用绝对路径执行 `docker version`；若仅受限上下文失败而授权终端成功，记录为执行权限/沙箱边界，不修改 Compose 或数据库配置。
3. 在具备 Docker CLI 执行权限的终端验证 `docker version`、`docker compose version` 和 `docker compose config --quiet`。
4. CLI/Engine 恢复后，再按项目 Compose 的 `migrate`、Backend、Worker、Dispatcher 顺序检查服务状态和日志。

### 本次案例结论

本次 Docker CLI 文件和 Engine 均正常，初始失败来自受限执行上下文的“拒绝访问”；授权后 Docker 诊断、Compose 配置、数据库迁移、健康检查和双账号登录均通过。该案例是“CLI 找不到或 Engine 未运行”案例的执行权限分支，不是新的 Docker 安装问题。

### 本次验证结论

- Docker Desktop 4.83.0、Engine 29.6.2、Compose 5.3.1 和 `desktop-linux` context 均正常。
- 旧容器因未执行 Alembic，Dispatcher 报 `async_task_runs` 不存在；退出码 137 是旧栈停止后的结果，不是 Docker Engine 故障。
- 当前 Compose 已增加一次性 `migrate` 服务；修正迁移枚举重复创建后，迁移、健康检查和两个预置账号登录均通过，重复启动也可正常完成。
