# 阶段 2：外部技术能力预验证与复用复核记录

## 1. 复用判定原则

本阶段不因候选人资料准备模块已经使用过某项能力而自动跳过验证。只有在以下条件同时满足时，才可复用既有真实证据：

- 供应商、工具/API 契约和版本未改变；
- 凭证注入边界、网络拓扑、超时和成本边界未改变；
- 输入/输出 Schema、失败映射和首个真实消费者的使用方式没有改变；
- 既有记录包含最小真实调用，而不是 Mock、单元测试或仅配置存在。

满足条件时，本变更不重复执行同一供应商级验证，但必须在本记录登记复用来源、适用范围和未覆盖边界。复用证据不能替代当前变更的 Worker → 外部服务 → 原子终态集成验收。

## 2. 能力验证矩阵

| 能力 | 本次使用方式 | 既有真实证据 | 复用结论 | 当前缺口/边界 |
| --- | --- | --- | --- | --- |
| PostgreSQL / Repository | 复用候选人资源归属、任务和画像持久化边界 | `CHG-2026-020/02-validation/prevalidation.md`；`CHG-2026-020/06-verification/test-report.md` 子任务 0–3、7 | `passed`（复用） | 本记录不替代本模块后续画像/简历/任务同事务验收 |
| 受控对象存储 | Worker 按 `stored_file_object_id` 受控读取正式简历 | `CHG-2026-020/06-verification/test-report.md` 子任务 2、3；真实本地对象存储上传、对象复用、归属隔离和清理验证 | `passed`（复用） | 解析 Worker 的完整读取→MinerU→终态链路留待本模块集成验收 |
| Redis Broker | Celery Broker，承载 `resume_parse` 投递 | `CHG-2026-020/06-verification/test-report.md` 子任务 4；`worker-prevalidation.md` 2026-08-01 真实 Compose Worker 消费证据 | `passed`（复用 + 真实复验） | 不替代 G2→G3 跨包业务联调或本模块阶段 6/8 验收 |
| Dispatcher | 扫描 `async_task_runs` 并可靠投递 | `CHG-2026-020/06-verification/test-report.md` 子任务 4；`worker-prevalidation.md` 2026-08-01 正式 Dispatcher 投递和 Worker 接管证据 | `passed`（复用 + 真实复验） | 不替代 G2→G3 跨包业务联调或本模块阶段 6/8 验收 |
| MinerU MCP | Worker 受控临时 PDF 的文本提取 | `CHG-2026-020/06-verification/test-report.md` 子任务 5；`worker-prevalidation.md` 2026-08-01 真实 Worker 成功画像证据 | `passed`（复用 + 真实复验） | 不替代本模块阶段 6/8 的完整业务验收 |
| Qwen Plus 结构化输出 | 从内存 Markdown 生成严格画像 Schema | `CHG-2026-020/06-verification/test-report.md` 子任务 6；`worker-prevalidation.md` 2026-08-01 真实 Worker 成功画像证据 | `passed`（复用 + 真实复验） | 不替代本模块阶段 6/8 的完整业务验收 |
| Celery Worker | 领取执行租约、受控读取、调用解析器、重试并写入终态 | `worker-prevalidation.md` 2026-08-01 后续补录：真实 Compose Worker 启动、Redis 消费、数据库租约、MinerU/Qwen 成功画像、重复投递和 Worker 中断后重投递接管 | `passed`（真实复验） | 不代表 G2→G3 跨包业务联调或本模块阶段 6/8 全链路验收 |

## 3. 安全与证据边界

- 既有证据未记录凭证、简历正文、Markdown、路径、对象键、模型原始响应或异常堆栈；本次只引用脱敏的验证事实和关联文件路径。
- MinerU/Qwen 的复用 `passed` 仅表示供应商契约和最小真实调用已验证，不表示本模块的 Dispatcher → Worker → MinerU → Qwen → Pydantic → 原子终态全链路已验收。
- `CHG-2026-020` 阶段 2 的裁决“资料准备模块不验证解析技术能力”仍然有效；本记录没有把该模块的解析能力误记为已验收，只复用其后续验证记录中明确存在的真实证据。

## 4. 阶段 2 结论

技术预验证结论：`passed`（既有证据复用 + Worker 真实复验）。

通过理由：供应商、工具/API 契约、拟运行拓扑、凭证注入边界、输入输出 Schema 和失败映射均未发生变化；既有 MinerU、Qwen、Redis、Dispatcher、对象存储和 PostgreSQL/Repository 证据可复用，且 `worker-prevalidation.md` 的后续真实复验已经补足 Worker 启动、Redis 消费、数据库租约、成功终态、重复投递和 Worker 中断接管证据。本次没有新增需要供应商级首次验证的外部技术能力。

适用边界：本结论只证明外部技术能力可作为 CHG-021 实现前置能力复用，不等同于 G2→G3 跨开发包业务联调、完整解析验收或画像模块阶段 6/8 通过。本次人工复核已完成，阶段台账已将阶段 2 标记为 `passed`；阶段 3 及后续阶段仍须按串行门禁推进。
