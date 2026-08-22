# IS-S10-02 Acceptance Artifact

> 验收日期：2026-08-20
> 当前交付状态：`integration_delivered`

## 执行命令与结果

| 验证项 | 命令/环境 | 结果 |
| --- | --- | --- |
| 确定性 Capability Acceptance | `uv run pytest tests/acceptance/s10_02_document_delivery -m capability_acceptance -o addopts='-q'` | 6 passed |
| PostgreSQL/对象存储集成 | `RUN_INTEGRATION_TESTS=true TEST_DATABASE_URL=<脱敏本地测试连接> uv run pytest tests/integration/test_s10_document_delivery.py -q --no-cov` | 1 passed |
| 数据库迁移 | `uv run alembic upgrade head` | `20260820_0015 → 20260820_0016` 成功 |
| 前端回归 | `npm run typecheck`；`npm run lint`；`npm run test:run`；`npm run build` | 通过；21 files / 69 tests |

## 固定 Fixture 边界

- 仅使用脱敏 CandidateDocument 元数据和非零字节占位文件。
- 验证文件名：`candidate_certificate.pdf`、`candidate_photo.jpg`、`candidate_proof.png`、`学籍验证报告.pdf`。
- 请求先提取明确的资料名称，再按文件名标准化、关键词和受控别名匹配；不读取文件内容，不调用 LLM、OCR、Embedding 或 LangChain。
- 每个主演示请求只有一个匹配文件；多命中仅验证安全拒绝，不作为主演示关闭条件。

## 验收结果

- 每次成功请求产生一条 Agent 文本消息和一个 `MessageAttachment`。
- 同一 `client_message_id` 重复提交复用原消息、AgentTurn 和附件；重复下载不创建新消息或附件。
- 附件创建后 7 天内可下载；删除 CandidateDocument 后仍可下载；过期后返回受控 `410`。
- 跨 Application 复用同一 CandidateDocument；HR、Application、Conversation 和 Candidate 归属链完成隔离校验。
- 附件投影只包含文件名、格式、大小、创建/过期时间和状态；未返回 CandidateDocument ID、StoredFileObject ID、对象键、路径、公开 URL 或正文。
- 对象清理将未过期 MessageAttachment 视为有效引用；过期后才允许回收底层对象。

## 敏感信息与失败分类

Artifact 不记录文件正文、联系方式、文件路径、对象存储定位、Prompt、工具输入或模型原始响应。未找到、失效、过期、无权和对象缺失均使用受控消息/状态；S10-02 本次未新增 LLM 外部调用证据。

## 2026-08-21 补充真实前端复测与整改回归

开发者在真实沟通页发现并完成整改：

1. 成功交付仍显示“已为你找到相关求职资料，请点击附件下载。”等额外文字；预期是 Agent 消息不显示文本，只返回文件附件。
2. 附件当前展示为普通消息气泡、下载按钮和混排元数据；预期改为仿微信接收文件的文件卡片效果，清晰展示文件信息和下载入口。

| 问题编号 | 类型 | 整改目标 | 状态 |
| --- | --- | --- | --- |
| `S10-02-001` | `contract_mismatch` / `backend_implementation_error` | 成功资料交付的 Agent Message `content` 为空字符串，不显示额外成功提示语 | 已完成 |
| `S10-02-002` | `frontend_mapping_error` | 附件按仿微信文件接收效果重构，保留下载、失败重试和过期状态，不提供预览 | 已完成 |
| `S10-02-003` | `backend_implementation_error` | “学籍证明”“学籍材料”“学籍验证报告”及带“材料”的表述均能命中对应学籍资料 | 已完成 |

整改回归覆盖空正文附件消息、文件卡片元数据、学籍资料受控别名匹配、下载失败重试和过期禁用；以上问题已关闭，不影响本 Artifact 已记录的文件名匹配、附件生命周期、权限、幂等和下载验证。

## 历史验收结论

S10-02 的后端迁移、确定性文件名匹配、空正文附件消息、下载生命周期、权限/幂等、对象清理保护和前端文件卡片均已验证，`IS-S10-02` 标记为 `integration_delivered`。在线预览和正文检索不属于本次交付；S10-03 已由独立 `IS-S10-03` Scenario 交付。
