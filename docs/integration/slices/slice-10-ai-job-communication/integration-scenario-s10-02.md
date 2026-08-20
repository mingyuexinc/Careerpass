# Integration Scenario：S10-02 资料附件交付

> Scenario ID：`IS-S10-02`
> Integration Contract：[`IC-S10-AI-COMMUNICATION@0.4`](./integration-contract.md)
> 关联 Slice：S10 AI 求职沟通
> 交付状态：`integration_blocked`（后端核心能力已通过；补充前端展示问题待整改回归）

## 1. 场景目标

在 S-08 已创建 Application 和 Conversation、S-05 已保存 CandidateDocument 的前提下，HR 在当前投递会话中请求证书、照片或证明等资料。系统只按文件名语义确定性匹配一个资料，写入一条 `content` 为空的 Agent 消息并关联一个 `MessageAttachment`，HR 只看到仿微信接收文件效果的附件卡片并可重复下载。

本场景只验收文件名语义和附件交付，不读取文件内容，不预览，不使用 LLM，不改变 Application 状态。

## 2. 固定 Fixture 与执行入口

Fixture 使用脱敏 CandidateDocument 元数据和非零字节的空白/占位文件，仅用于验证文件名语义；不把文件正文作为测试输入或断言依据。每个请求只配置一个符合语义的文件，不把多命中作为主演示条件。

| 文件名 Fixture | 请求示例 | 预期匹配 |
| --- | --- | --- |
| `candidate_certificate.pdf` | “请提供候选人的证书” | `candidate_certificate.pdf` |
| `candidate_photo.jpg` | “请提供候选人的照片” | `candidate_photo.jpg` |
| `candidate_proof.png` | “请提供候选人的证明材料” | `candidate_proof.png` |
| `学籍验证报告.pdf` | “请把你的学籍验证报告发一下。” | `学籍验证报告.pdf` |

自动验收命令：

```text
uv run pytest tests/acceptance/s10_02_document_delivery -m capability_acceptance -o addopts='-q'
```

测试目录：`careerpass-backend/tests/acceptance/s10_02_document_delivery/`

Acceptance Artifact：`docs/integration/slices/slice-10-ai-job-communication/artifacts/IS-S10-02-acceptance.md`

Artifact 必须记录实际命令、测试结果、脱敏 Fixture 边界、下载有效期和失败分类；不得记录文件正文、对象存储定位、联系方式、Prompt 或模型原始响应。

## 3. 主验收路径

| 步骤 | 操作 | 预期结果 |
| --- | --- | --- |
| 1 | HR 登录并进入由 S-08 创建的当前 Conversation | 会话可见；不需要点击候选人创建会话 |
| 2 | HR 发送证书、照片或证明请求 | 请求携带稳定 `client_message_id`，服务端按文件名匹配一个 CandidateDocument |
| 3 | 读取新增消息 | 新增一条 `content` 为空的 Agent 消息，关联一个 `MessageAttachment`；不新增第二条附件消息 |
| 4 | 检查附件卡片 | 只显示仿微信接收文件效果的文件卡片、文件名、格式、大小、创建时间、过期时间和下载状态；不显示“已为你找到”等额外提示语、内部 ID、对象定位或正文 |
| 5 | 重复下载同一附件 | 7 天有效期内可重复下载，不要求额外确认或重新登录；每次仍通过 HR/Application/Conversation 归属校验 |
| 6 | 删除 CandidateDocument 后再次下载 | 已发送附件在有效期内仍可下载；下载能力不依赖当前 CandidateDocument 记录仍存在 |
| 7 | 在同一 Candidate 的另一 Application 中请求同一资料 | 允许复用 CandidateDocument，但每条消息和附件仍归属于各自 Application Conversation |
| 8 | 重复提交同一 `client_message_id` | 复用原 Agent 消息和附件，不新增 Message、AgentTurn 或 Attachment |

## 4. 安全与隔离验收

- 越权 HR、越权 Application、越权 Conversation、跨 Candidate 访问均返回安全的 403/404 结果，不泄露真实归属。
- 普通消息和附件投影不返回 CandidateDocument ID、文件路径、对象键、公开 URL、文件正文或其它候选人资料。
- 附件下载失败、附件过期、资料未找到或资料已失效时返回受控失败/友好文本，不泄露内部原因。
- 附件正文不进入 LLM、日志、普通 JSON 响应或诊断 Artifact；本场景不产生 Qwen 调用证据。

## 5. 非目标与关闭条件

本场景不关闭多资料同时命中、文件正文检索、OCR、Embedding、LLM 语义理解、在线预览、候选人二次授权、S10-03 主动 query 或真实外部平台发送。未找到和失效资料只要求具备受控友好回复，不作为主演示关闭条件；Fixture 保证主路径只有一个匹配文件。

## 6. 实际验证结果

- Capability Acceptance：6 项通过，覆盖证书、照片、证明、学籍验证报告文件名匹配、真实 Fixture 存在性和多命中安全拒绝。
- PostgreSQL/对象存储联调：迁移 `20260820_0016`、单 Agent 消息单附件、幂等、删除 CandidateDocument 后下载、7 天过期和对象清理引用保护通过。
- API/安全投影：附件下载接口返回文件流和安全响应头；普通消息与附件投影不包含 CandidateDocument、StoredFileObject 或存储定位字段。
- 前端：真实附件字段映射、下载中/成功/失败/过期状态和仅下载交互已完成验证；补充复测发现成功提示语和附件卡片视觉效果不符合新的交付预期。
- 本场景未调用 LLM，未读取文件正文；后端核心能力无阻断，但前端展示整改尚未完成。

## 7. 补充联调发现的问题

| 记录编号 | 问题类型 | 发现结果 | 整改目标 | 当前状态 |
| --- | --- | --- | --- | --- |
| S10-02-001 | `contract_mismatch` / `backend_implementation_error` | 资料匹配成功后，Agent 消息仍带有“已为你找到相关求职资料，请点击附件下载。”等成功提示语。 | 成功交付时 Agent Message 的 `content` 为空字符串，用户可见内容只有附件，不发送额外成功提示语。 | 待整改 |
| S10-02-002 | `frontend_mapping_error` | 附件当前以普通消息气泡、按钮和混排元数据显示，文件接收效果弱，不符合微信式文件消息的直观交互。 | 将附件重构为仿微信接收文件卡片：文件图标/类型、文件名、格式、大小、必要时间信息和下载入口层次清晰；保留下载、失败重试和过期状态，不提供在线预览。 | 待整改 |

以上问题不否定文件名匹配、附件持久化、权限、幂等、下载和有效期等后端核心验收结果，但在整改和开发者回归前不能关闭本场景。

## 8. 当前关闭结论

核心能力验收：`是`；前端展示整改完成：`否`；当前场景状态：`integration_blocked`。S10-03、在线预览和正文检索仍不属于本次交付。
