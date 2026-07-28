# MinerU MCP 集成技术方案

## 1. 目的与适用范围

本文是 CareerPass 对正式简历使用 MinerU MCP 的唯一技术集成依据，定义 MCP Client/Server 职责、部署方式、凭证边界、受控文件输入、超时和验收要求。

本文仅适用于 `resumes` 的文本提取。`candidate_documents` 不进入 MinerU；画像生成、Qwen 调用、结构化校验和任务终态写入由其他技术方案定义。

## 2. 核心概念

| 组件 | 职责 | CareerPass 中的位置 |
| --- | --- | --- |
| MCP Client | 建立 MCP 会话并调用工具 | Celery Worker 内的 MinerU 适配器 |
| MCP Server | 暴露 `parse_documents` 等 MCP 工具 | MVP 为同机官方 `mineru-open-mcp` Bridge；远程 MCP 为条件方案 |
| MinerU 解析服务 | 生成 Markdown | 由同机 Bridge 调用 MinerU 能力 |
| CareerPass Adapter | 临时文件、工具参数、结果归一化和失败分类 | `app/infrastructure/mineru_mcp.py` |

Worker 是 MCP Client，不等于 MCP Server。MVP 的 stdio 模式下，Worker 受控创建官方 MCP Bridge 子进程；该子进程才是 MCP Server，且不对外暴露网络端口。

## 3. 部署模式与 MVP 裁定

### 3.1 MVP 首选：同机官方 MCP Bridge（stdio，已验证）

```text
CareerPass Celery Worker (MCP Client)
  -> stdio
mineru-open-mcp（官方 MCP Server 子进程）
  -> MinerU cloud parsing capability
```

- Worker 通过固定受控命令 `uvx mineru-open-mcp` 创建子进程，以 MCP stdio 会话调用工具；不监听业务网络端口。
- 从本机安全配置读取 `MINERU_API_KEY`，仅在创建 Bridge 子进程时映射并注入为 `MINERU_API_TOKEN`。令牌不出现在命令行参数、API、数据库、日志、追踪或前端配置中。
- Bridge 与 Worker 运行在同一受控主机/容器中，因此 `parse_documents` 可接收由 Worker 创建的本地临时 PDF 路径；该路径绝不来自用户、Agent 或模型。
- 2026-07-27 已完成最小连接验证：使用本机配置的令牌启动 stdio Bridge，MCP `initialize` 和 `tools/list` 成功，发现 `parse_documents`、`get_ocr_languages`。该证据仅证明连接与工具发现，不等同于文件解析验收。

### 3.2 条件方案：MinerU 托管的远程 MCP

```text
CareerPass Celery Worker (MCP Client)
  -> HTTPS / MCP
MinerU Remote MCP Server
  -> MinerU parsing capability
```

- 仅在 MinerU 明确提供可用的远程 MCP 鉴权方式、已通过 `initialize`/`tools/list` 验证，且工具输入 Schema 已验证时启用。
- 当前曾以 `Authorization: Bearer <MINERU_API_KEY>` 连接 `https://mcp.mineru.net/mcp`，在工具发现阶段收到 HTTP 401；同时同一令牌调用 MinerU Open API 的受控鉴权检查成功。因此不得将该远程地址或 Bearer Header 形式视为本项目可用的 MCP 接入契约。
- 若未来启用，必须单独记录远程服务端要求的认证契约和受控输入方式；未满足任一条件时远程模式为 `blocked`，不得替换已验证的 stdio 方案。

## 4. 配置与凭证

| 配置 | MVP 要求 | 安全规则 |
| --- | --- | --- |
| `MINERU_API_KEY` | 必填；映射为 MinerU 所需令牌 | `SecretStr`；绝不记录值 |
| `MINERU_MCP_TRANSPORT` | MVP 固定为 `stdio` | 固定受控枚举，禁止请求输入；远程模式须完成独立验收才可配置 |
| `MINERU_MCP_COMMAND` | `uvx` | 固定受控命令，不由模型或 API 提供 |
| `MINERU_MCP_COMMAND_ARGS` | `mineru-open-mcp` | 固定受控参数；不得携带令牌或用户输入 |
| `MINERU_MCP_URL` | 仅条件远程模式必填 | 仅允许已验收的 HTTPS Endpoint；当前不作为 MVP 运行配置 |

凭证存在性不证明服务可用。可用性必须由显式开启的外部集成测试，以脱敏受控 PDF 完成一次实际 `parse_documents` 调用来证明。

## 5. 调用边界

1. Worker 从数据库执行租约取得 `resume_id` 和 `execution_token`。
2. Repository 仅在简历仍为 `processing` 且关联对象为 `ready` 时返回受控文件。
3. MVP stdio 模式由对象存储适配器在 Worker 私有临时目录写入系统创建的随机临时 PDF，并仅将其本地路径传给 Bridge。路径不得由用户、Agent 或模型提供，解析完成或失败后必须清理。远程模式如未来启用，另按其已验收的输入契约实施。
4. MCP Client 仅调用官方 `parse_documents`；不接受模型拼接的工具名、URL、Shell 命令或参数。
5. 适配器只将 Markdown 保留在内存中交给后续 Qwen 链路；不保存 MCP 原始 JSON、输出目录、下载地址或临时路径。
6. 成功、重试、终态失败与画像写入均受相同 `execution_token` 和后续业务事务约束。

官方 MCP 文档将 `parse_documents` 作为公开工具契约，但未将 `pipeline` 明确列为稳定工具参数。项目不得假定任意 Server 版本支持 `mode="pipeline"`。若 MVP 强制 pipeline，必须先根据实际官方 Server 的 `tools/list` 结果确认参数；不能确认时应切换到官方 CLI/API 路线或将能力标记为 `blocked`。

## 6. 安全、超时与失败映射

| 情况 | 是否重试 | 失败分类 |
| --- | --- | --- |
| MCP 调用超时 | 是 | `parser_timeout` |
| 网络错误、429、5xx、服务暂不可用 | 是 | `internal_error` |
| 受控对象不可读或不在 `ready` | 是 | `storage_unavailable` |
| PDF 不可读、无有效机器文本或 MCP 返回空 Markdown | 否 | `file_unreadable` |

- 超时、最大重试和退避遵从《Async task technical design》。
- API、日志、Celery 事件和 LangSmith 仅记录关联 ID、阶段、受控失败分类、重试次数和耗时；不得记录文档正文、路径、原始 MCP 响应或令牌。
- 旧执行租约回调必须因 `execution_token` 不匹配而安全忽略。

## 7. 安装、运行与验收

### 同机 stdio Bridge（MVP 首选）

1. 在受控 Worker 镜像或宿主中提供并锁定 `uvx` 与官方 `mineru-open-mcp`。
2. 以最小权限账户运行；创建子进程时仅通过环境变量注入 `MINERU_API_TOKEN`。
3. 使用 MCP `initialize` 与 `tools/list` 作为无文件、无解析成本的连接门禁。2026-07-27 的验证已通过，工具列表含 `parse_documents` 与 `get_ocr_languages`。
4. stdio 不开放监听端口。随后显式设置 `RUN_EXTERNAL_INTEGRATION_TESTS=true`，使用受控脱敏 PDF 调用 `parse_documents`，验证非空 Markdown 和临时文件清理。

### 远程 MCP（条件方案）

1. 先取得 MinerU 对远程 MCP 的正式鉴权及输入 Schema 说明，并将其作为本设计的补充证据。
2. 使用不含文件内容的 `initialize` 与 `tools/list` 验证；HTTP 401、工具缺失或 Schema 不兼容均视为 `blocked`。
3. 仅在上述门禁通过后，才针对已批准的受控输入方式进行脱敏 PDF 外部集成验收。

验收至少证明：MCP 会话建立、官方工具可发现、`parse_documents` 返回非空 Markdown、临时文件清理、敏感信息未外泄，以及超时/限流/服务错误遵循既定失败分类。未满足任一条件时，不得将 MinerU 外部集成标记为通过。

## 8. 非目标

- 不允许前端、Agent 或 LLM 直接调用 MCP。
- 不建立通用文件解析中心、用户可见 MCP 配置页或动态工具路由。
- 不以 Flash 模式替代需要正式令牌的生产解析路径。
- 不将 OCR、扫描件兼容或解析质量调优纳入当前候选人资料准备 MVP。
