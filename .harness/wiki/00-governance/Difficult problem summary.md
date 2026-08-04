# 疑难问题汇总

本文档用于沉淀开发过程中具有复用价值的环境、依赖、架构、联调和故障排查案例。案例只记录必要的诊断信息，不记录凭证、敏感原值、简历正文或生产数据定位信息。

## 使用规则

1. 遇到疑难问题时，先查询本文档，确认是否已有相同或相近案例。
2. 已有案例适用时，优先复用其诊断路径和安全边界；若当前环境不同，必须重新确认事实，不得盲目套用结论。
3. 问题解决后，将具备复用价值的背景、原因、分析过程、解决方案和验证结果补充为新案例。

## 案例 1：Docker Desktop 已安装但无法启动隔离 Compose

### 背景

在 Celery Worker 真实能力预验证阶段，需要使用 `careerpass-backend/docker-compose.integration.yml` 启动隔离 PostgreSQL、Redis、Dispatcher 和 Celery Worker。开发者确认真实电脑已安装 Docker，但执行验证时系统无法识别 `docker` 命令，隔离 Compose 拓扑无法启动。

### 原因

问题由两个环境状态叠加造成：

- Docker Desktop 进程当时没有运行，Docker Engine 尚未提供服务；
- Docker CLI 位于用户级安装目录 `C:\Users\58280\AppData\Local\Programs\DockerDesktop\resources\bin`，该目录未进入当前 Codex 会话的 PATH，因此普通命令行显示找不到 `docker`。

这不是项目 Compose 文件、Redis、PostgreSQL 或 Celery 配置本身导致的启动失败。

### 分析过程

1. 先执行只读命令检查 `docker` 和 `docker compose` 是否可发现，确认当前会话 PATH 中不存在 Docker CLI。
2. 检查用户级 Docker Desktop 安装目录，确认 CLI 文件实际存在，并读取 Docker Desktop 版本信息。
3. 检查 Docker Desktop 进程和 Docker Engine 状态，确认 Desktop 未运行。
4. 启动 Docker Desktop 后，使用 CLI 的绝对路径执行 `docker version`，确认 Client/Server 均可用。
5. 使用绝对 CLI 启动隔离 Compose，并检查 PostgreSQL、Redis healthcheck、Dispatcher 和 Worker 状态。
6. 查看 Worker 日志，确认 Celery 已连接 Compose Redis、注册 `careerpass.resume_parse` 并进入 ready 状态。

### 解决方案

1. 启动用户已安装的 Docker Desktop，使 Docker Engine 可用。
2. 在当前验证会话中使用 Docker CLI 绝对路径，避免依赖未刷新的 PATH。
3. 通过隔离 Compose 启动验证拓扑，不触碰共享或生产环境。
4. 如需长期消除“命令找不到”现象，将 Docker CLI 安装目录加入用户 PATH，并重新打开终端/会话；该步骤属于环境维护，不是项目代码修复。

### 验证结果与边界

- Docker Engine/Compose 成功启动隔离拓扑。
- PostgreSQL 和 Redis healthcheck 通过。
- Celery Worker 成功连接 Redis，注册 `careerpass.resume_parse` 并真实消费任务。
- 后续验证仍需分别记录 Worker 任务终态、重试、租约、重投递和幂等证据；Docker 能启动不等于完整业务链路已通过。
- 诊断记录不得输出 API 密钥、数据库密码、简历原文、对象绝对路径或模型原始响应。
