# 后端故障排查

> 本文档记录可复用的后端环境、依赖和联调诊断案例。只保留必要的脱敏诊断信息。

## 使用规则

1. 每个新会话中的后端任务先完整读取本文档，并在首次工作进度中声明匹配案例或“未匹配既有案例”。
2. 先确认问题属于环境、依赖、架构还是业务实现。
3. 涉及 Docker、Compose 或基础服务 Readiness 时，先从后端根目录执行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend-readiness.ps1`。
4. 优先执行只读检查，不修改共享或生产环境。
5. 复用案例时重新验证当前机器和当前配置，不直接套用历史结论。
6. 新案例只记录原因、诊断路径、解决方法、验证边界和必要的关联文件。

统一预检只读取故障文档并检查 Docker CLI、Engine、Compose 和项目 Compose 配置，不启动、停止或修改容器。状态为 `execution_denied` 时，应在授权执行上下文重新运行同一脚本；状态为 `cli_not_found` 时，只能记录当前已检查位置未发现 CLI。

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

## 误判 Docker 未安装：CLI 已安装但当前 Shell 无法执行

### 现象与原因

执行 `docker --version` 返回“无法将 docker 识别为命令”，容易被误判为 Docker 未安装。若当前执行上下文还限制了命令发现或进程启动，实际原因可能是用户级 Docker CLI 已安装，但当前 Shell 未正确发现，或执行 `docker.exe` 时被拒绝访问。

本次 S-02 联调前的误判属于此类：Docker CLI 实际位于 `C:\Users\58280\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe`，当前 `PATH` 也包含对应目录；但受限执行上下文直接运行该文件返回“拒绝访问”。因此当时只能得出“当前上下文无法执行 Docker CLI”，不能得出“Docker 未安装”或“Docker Engine 未运行”。

### 正确诊断路径

1. 先用 `Get-Command docker -ErrorAction SilentlyContinue` 检查当前命令发现结果；命令未发现不等于 CLI 文件不存在。
2. 用 `Test-Path` 检查常见安装位置和当前 `PATH` 中 Docker 目录下的 `docker.exe`。
3. 若文件存在，使用已确认的绝对路径执行 `docker version`、`docker compose version` 和 `docker context show`。
4. 若绝对路径执行返回“拒绝访问”，记录为当前 Shell/沙箱执行权限问题；不得记录为“未安装”。
5. 只有在具备 Docker CLI 执行权限的终端中确认 `docker version` 的 Engine 部分失败后，才能判断 Engine 未启动或不可连接。
6. 只有完成上述检查后，才能继续执行项目 Compose 配置检查和服务启动。

### 结论边界

- `Get-Command` 找不到：只能说明当前 Shell 未发现命令；
- `Test-Path` 为真：说明 CLI 文件已安装；
- CLI 返回“拒绝访问”：说明执行上下文受限；
- CLI 能运行但 Engine 连接失败：才进入 Docker Engine/Context 排查；
- Docker Engine 可用但 Compose 服务失败：再排查项目 Compose、迁移和服务日志。

## Windows PowerShell 查看 JSON 响应出现中文乱码

### 现象与原因

API 已返回成功结果，但 Windows PowerShell 查看 `fields`、JD 原文或标题时出现乱码。若服务端 Parser 已按 UTF-8 读取 Markdown，且响应原始字节正确，常见原因是 JSON 响应头未声明 `charset=utf-8`，客户端按本地代码页解码。

### 诊断与处理

1. 用 `curl.exe -D -` 查看响应头，确认 `Content-Type` 是否为 `application/json; charset=utf-8`。
2. 对比响应原始字节和服务端受控 Markdown 的 UTF-8 字节，区分传输乱码与解析乱码。
3. 服务端统一为 JSON 响应补充 `charset=utf-8`，并增加响应头回归测试。
4. 重建 Backend 后再次调用 API；开发者重新核对 `fields` 原文、固定标题和额外字段。

### 结论边界

- Parser 使用 UTF-8 解码失败：属于输入不可用，应按 S-03 失败语义处理；
- Parser 输出字节正确但 PowerShell 显示乱码：属于 HTTP 客户端解码问题，不应修改字段内容或重新解析；
- 二次开发者 API 验收通过前，不得据此关闭 S-03 Scenario。

## Job 引用的 JD 对象被清理为 `deleting`

### 现象与原因

S-03 提交受控 JD 时返回 `controlled JD input unavailable`，路径存在且内容哈希正确，但数据库中对应的 `StoredFileObject` 已不是 `ready`。若该对象仍被活动 `Job` 引用，常见原因是对象清理逻辑只检查简历或候选人文档引用，遗漏了 `Job.stored_file_object_id`。

### 诊断与处理

1. 在不输出文件路径、对象键或正文的前提下，核对受控文件的内容哈希、登记状态和活动 Job 归属。
2. 检查对象清理 Repository 的“未引用”条件是否排除活动 Job 引用。
3. 在对象清理的认领和最终删除两个阶段均保护活动 Job 引用，并补充数据库集成回归测试。
4. 已被错误标记或物理文件已缺失的历史对象不能直接恢复为可用输入；应重新登记受控 JD，再执行 S-03 POST/GET 验证。

### 结论边界

- S-03 返回该通用错误不代表路径越界；它也可能表示对象未登记、未就绪、归属不匹配或历史对象已被清理；
- 修复清理逻辑只能防止后续误清理，不能恢复已经删除的物理文件；
- 只有重新登记并确认 `Job + StoredFileObject` 就绪后，才能继续 S-03 交付测试。

## MinerU 返回业务错误却被误当作 Markdown

### 现象与原因

固定 PDF 的 Capability Acceptance 显示解析成功，但画像字段全部为 `null` 或空数组。MinerU MCP 协议调用本身未报错，实际 `structuredContent.status=error`；客户端丢弃结构化结果并把 JSON 文本消息当作 Markdown 交给 Qwen，导致 Qwen 合法返回全空画像。当前网络还存在 MinerU 结果 CDN 经代理连接失败、直连正常的差异。

### 诊断与处理

1. 只记录 MCP 的 `isError`、结构化状态、结果数量和内容长度，不输出 Markdown、文件定位或原始错误；
2. 优先消费 `structuredContent`，检查顶层和单文件状态；依赖连接失败进入可重试失败，业务输入失败进入不可读失败；
3. MinerU Bridge 继承必要代理和证书环境，但将已验证的 MinerU 结果 CDN 加入子进程 `NO_PROXY`；
4. Qwen JSON Schema 要求每个属性都返回，并由 Pydantic 拒绝完全空画像；若源 Markdown 有明确的联系方式、教育、工作或项目章节而结果遗漏对应事实，同样视为无效输出；
5. Schema 无效或显式源事实漏抽时，适配器使用纠偏提示受控重试一次，连续遗漏则形成 `schema_validation_failed`；
6. 固定 PDF 验收必须断言姓名、联系方式至少一项、教育、工作或项目经历及 `matching_ready`，不能只断言模型对象存在。

### 验证边界

- MinerU 或 Qwen 依赖失败必须形成失败或重试，不得生成 CandidateProfile；
- 一般性核心字段缺失仍遵循 `parse_succeeded + matching_not_ready`，只有固定验收 PDF 因已知包含全部核心字段而要求 `matching_ready`；
- 外部调用总耗时必须低于 Worker 软/硬时限和执行租约，三者配置需保持一致。

## 简历字段有值但事实错误仍通过验收

### 现象与原因

Qwen 返回的画像通过 JSON Schema，但教育字段出现 Schema 名称、不同工作经历复用了同一公司，验收仍因字段非空而通过。原因是结构和存在性校验不能证明字段受源文支持；工作年限同时被错误地当作可选模型抽取值。

### 诊断与处理

1. 对姓名、联系方式、教育、公司、岗位和项目名称执行源文支持检查，不记录源文；
2. 拒绝 Schema 字段名作为业务值，并以源文出现次数检查无依据的公司重复；
3. 校验失败后只纠偏重试一次，连续失败形成 `schema_validation_failed`；
4. 工作年限排除实习、合并重叠年月并由代码确定性派生，不采用模型估算。
5. 对文本型 PDF 使用原生嵌入文本提取姓名、联系方式和教育，只让 Qwen 处理工作/项目语义关联；日期格式由代码标准化。

### 验证边界

- 该检查降低字段串位和 Schema 泄漏风险，不宣称仅靠字符串支持即可证明全部语义正确；固定 PDF 结果仍需开发者审阅；
- `unknown` 只表示所有非实习工作经历均缺少有效时间段，不等于解析失败。

## 宿主 MinerU 可用但 Worker 容器连续连接失败

### 现象与原因

宿主 Shell 的固定 PDF 解析可调用 MinerU，但真实异步链路在 Worker 中连续形成 `stage=mineru failure_code=internal_error`。宿主代理监听 `127.0.0.1` 时，该地址在容器内指向容器自身；Compose 未显式传入容器可达代理地址会导致稳定连接失败。

### 诊断与处理

1. 只检查宿主和容器代理变量是否存在及代理主机类型，不输出凭据或完整配置；
2. 在未提交的 `.env` 中将 `CAREERPASS_CONTAINER_PROXY` 配置为 `http://host.docker.internal:<port>`；
3. 将已验证版本的 `mineru-open-mcp` 固定安装进 Worker 镜像，任务直接执行预装命令，不使用 `uvx` 动态下载；
4. Compose 只向 Worker 映射该容器专用代理，MinerU Bridge 继续把结果 CDN 加入 `NO_PROXY`；
5. 重建 Worker 后重新执行真实异步链路。

### 验证边界

- 宿主能力通过不能证明容器网络可用；Worker 就绪也不能证明 MinerU 外部调用成功；
- 不得把宿主 `127.0.0.1` 代理值原样写入容器环境。
- S-04 文本型 PDF 不应被 MinerU 可用性阻断：原生嵌入文本成功时不调用 MinerU，只有本地无文本时进入 MinerU 回退。
