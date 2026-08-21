# Integration Contract：S10 AI 求职沟通

> Contract ID：`IC-S10-AI-COMMUNICATION@0.5`
> 关联 Slice：S10 AI 求职沟通
> 关联 Scenario：`IS-S10-01`、`IS-S10-02`、`IS-S10-03`
> 状态：`locked`

## 1. 用户场景与边界

- 角色：已登录并有权访问当前 Application 的 HR；
- 前置条件：岗位匹配完成，当前投递已建立 Conversation，S-07 绑定 Resume 可用；
- 触发：S-08 成功创建 Application 后初始化 Conversation，HR 在当前 Conversation 发送消息；
- 结果：HR 看到 S10-01 Agent 正式文本消息，或看到 S10-02 仅包含安全附件投影的 Agent 消息；S10-02 匹配成功时不显示“已为你找到”等额外成功提示语；
- 会话范围：只读取和写入当前 Application 对应的 Conversation；
- 不包含：其它岗位/Candidate/Application 会话、真实外部消息和 Application 状态变化；S10-02 附件交付仅限本 Contract 定义的文件名语义检索和单附件下载。

业务语义引用 [`business-baseline.md`](../../../business/business-baseline.md) 的 `BF-RULE-045` 至 `BF-RULE-057`，Slice 细化引用 [`slice-spec.md`](../../../../careerpass-backend/docs/development/slices/slice-10-ai-job-communication/slice-spec.md)。

会话初始化交接为 `APPLICATION-CONVERSATION@0.1`，由 S-08 在 Application 创建事务内幂等写入唯一 Conversation 容器；不写入欢迎消息。

## 2. 请求契约

### 2.1 HR 发送消息

```text
POST /api/v1/applications/{application_id}/conversation/messages
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "conversation_id": "uuid",
  "client_message_id": "client-generated-id",
  "content": "HR 的消息内容"
}
```

约束：

- 当前身份必须是 HR；服务端校验 `HR → Job → Application → Conversation` 归属链；
- `content` 非空且为文本；
- `client_message_id` 在当前 Conversation 内幂等；
- 不接受 Candidate ID、Job ID、对象存储路径或外部 URL 作为授权依据或附件来源。

### 2.2 HR 读取当前会话列表

```text
GET /api/v1/applications/hr/current/conversations
Authorization: Bearer <access_token>
```

返回当前 HR 有权访问的当前首轮 Conversation、安全岗位/候选人摘要和 `sent` 文本消息。

### 2.3 读取当前 Conversation

```text
GET /api/v1/applications/{application_id}/conversation/messages?conversation_id={conversation_id}
Authorization: Bearer <access_token>
```

只返回当前 HR 可见的当前 Application Conversation 文本消息。

### 2.4 S10-02 资料附件请求

S10-02 复用 `POST /api/v1/applications/{application_id}/conversation/messages` 消息入口。服务端从明确的资料请求语句提取请求名称，并执行 CandidateDocument 文件名标准化、关键词和受控别名匹配；不读取文件内容，不使用 LLM，每次请求最多选取一个 Fixture 保证的匹配资料。

匹配成功时，系统写入一条 Agent 消息并关联一个 `MessageAttachment`；该消息的 `content` 为空字符串，用户可见内容只有附件。HR 不需要额外确认或重新登录即可重复下载；服务端每次下载仍校验当前 HR、Application 和 Conversation 归属。附件自创建时间起 7 天有效，CandidateDocument 删除不影响有效期内已发送附件的独立下载能力。

下载使用受保护的附件下载接口，不在消息投影中返回文件路径、对象键、公开 URL 或原文件内容。未找到、资料失效或附件过期时返回安全的受控结果，不泄露内部原因。

## 3. 响应契约

所有 API 响应遵循 `{code, msg, data}`。文件下载成功时返回受控文件流；下载失败仍使用统一错误语义。

### 3.1 消息入口成功

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "conversation_id": "uuid",
    "received_message": {
      "id": "uuid",
      "sender": "hr",
      "message_type": "text",
      "status": "sent"
    },
    "agent_turn": {
      "id": "uuid",
      "scene": "resume_answer",
      "turn_status": "completed",
      "outcome": "message_sent",
      "retryable": false
    },
    "new_messages": [
      {
        "id": "uuid",
        "sender": "agent",
        "message_type": "text",
        "status": "sent",
        "content": "Agent 回复",
        "attachments": []
      }
    ]
  }
}
```

### 3.2 安全消息投影

`MessageView` 只允许返回 `id`、`sender`、`message_type=text`、`status`、`content`、`created_at` 和可选的 `attachments`。S10-02 附件投影每条 Agent 消息最多一个，字段如下：

| 字段 | 语义 |
| --- | --- |
| `id` | 附件消息关联的安全附件标识，用于调用下载接口 |
| `file_name` | 原资料文件名 |
| `file_type` | 文件格式 |
| `file_size_bytes` | 文件大小 |
| `created_at` | 附件创建时间 |
| `expires_at` | 创建后 7 天的失效时间 |
| `status` | `downloadable` 或 `expired` |

投影不返回 CandidateDocument 内部 ID、文件路径、对象键、公开存储地址、原文件内容、证据摘要、Prompt、Tool 输入或模型原始响应。

## 4. 场景映射

| 场景 | 输入 | 关键输出 | 可见结果 |
| --- | --- | --- | --- |
| S10-01 简历问答 | HR 关于经历、项目、技能的问题 | Agent 文本消息 | HR 只看到回答，不看到简历原文或证据摘要 |
| S10-02 资料附件 | HR 请求证书、照片或证明等资料 | `content` 为空的 Agent 消息 + 一个附件安全投影 | HR 只看到仿微信文件接收效果的附件卡片，可查看元数据并重复下载，不可预览或看到内部定位 |
| S10-03 主动 query | 进入当前 Conversation 后幂等触发，按会话历史最多保留一个 query | Agent 唯一 query 或静默结果；后续继续/停止固定回复 | HR 可见 query 和固定判断回复；等待/解析失败不可见额外提示 |

## 5. 状态与错误

### 5.1 Agent Turn 状态

```text
accepted → processing → completed
                    ↘ waiting
                    ↘ failed
```

| 状态/结果 | 前端或验收含义 |
| --- | --- |
| `completed/message_sent` | Agent 文本消息已写入并可见 |
| `completed/tool_failed` | Qwen 失败时已写入受控模板消息；`failure_code` 仅在内部 AgentTurn 保存 |
| `waiting/query_sent` | 主动 query 已发送，等待 HR 回答 |
| `waiting/pending` | 未收到或未识别到有效二元回答；不追问、不判断，后续明确回答仍可完成 |
| `completed/continue` | HR 明确回答后发送“好的，了解” |
| `completed/stop` | HR 明确回答后发送“感谢沟通，当前不考虑这个岗位了” |
| 无 AgentTurn/空消息 | 没有可提问条件时静默结束 |

### 5.2 错误语义

| 场景 | 统一错误/结果 | 页面或验收表现 |
| --- | --- | --- |
| 未登录 | 401 | 返回登录入口 |
| 非 HR 或无权访问 | 403/安全资源不可用 | 不泄露资源详情 |
| Conversation 不属于 Application | 404/安全资源不可用 | 不泄露真实归属 |
| S10-01 绑定 Resume-derived 经历范围完整，且存在性问题的目标能力未出现在该范围 | 200，Agent 否定事实消息 | 明确说明“没有相关经历”；允许补充已记录的其它相关经历，但不得展示证据摘要 |
| S10-01 检索、生成或校验失败且通道可用 | 200，Agent 模板消息 | “暂时无法回答当前问题” |
| S10-01 消息通道失败且重试耗尽 | 业务失败 | 不追加 Agent 回复 |
| S10-03 没有可提问条件 | 200，`agent_turn=null`、`new_messages=[]` | 静默，不发送消息 |
| S10-03 重复触发 | 原 `goal_query` 结果幂等返回 | 不重复追加 query |
| S10-03 未回答/解析失败 | 200，当前 HR turn 为 `pending`，不追加 Agent 消息 | 保持待处理，不追问、不作继续/停止判断 |
| S10-03 明确二元回答 | 200，继续或停止固定回复 | 不改变 Application、Match 或投递状态 |
| 请求重复 | 原结果幂等返回 | 不重复追加消息或附件 |
| S10-02 未找到或资料失效 | 200，Agent 友好受控文本消息 | 不创建附件，不泄露内部原因 |
| S10-02 匹配成功 | 200，Agent 消息 `content` 为空并带一个附件 | 不展示额外成功提示语；页面只展示附件文件卡片 |
| S10-02 附件准备失败 | 业务失败或受控文本结果 | 不产生半成品可见附件消息 |
| S10-02 附件过期 | 受保护下载接口返回安全失败 | 页面展示附件已过期，不返回对象定位 |

### 5.3 重试

- 首次尝试之外最多自动重试 2 次；退避参数由后端配置控制；
- 重试必须复用原幂等键；
- HR 重复提交同一 `client_message_id` 时返回原 Agent Turn 结果；
- 重试耗尽不改变 Application 状态，不产生外部消息。

## 6. 可见性与安全

- HR 可见：消息正文、发送主体、状态、时间以及附件文件名、格式、大小、创建/过期时间和下载状态；
- HR 不可见：Resume 原文、证据片段、CandidateProfile 全量、Prompt、Tool 输入、Agent 原始响应、审计记录和内部文件定位；
- 日志和追踪只记录关联 ID、场景、阶段、状态、错误分类、耗时和重试次数；
- 所有消息、附件和下载请求都必须经过当前用户、Candidate、Job、Application 和 Conversation 归属校验；“可重复下载”不等于跳过服务端鉴权。

## 7. 兼容与锁定记录

- 新增可选字段保持向后兼容；删除字段、改变状态含义或改变附件预览/下载能力必须升 Major 版本；
- API、状态、权限、附件能力或 Application 影响范围变化时，必须回退 Slice Design 并同步业务基线、技术设计和 Scenario；
- `0.4` 保持 S10-01 请求/响应字段兼容并承载 S10-02 附件交付；
- `0.5` 在保持 `0.4` 兼容的前提下新增 S10-03 主动触发、AgentTurn `goal_query/goal_judgement`、等待/待处理/继续/停止结果和无消息静默结果；不改变 Application、Match 或投递状态。

## 8. S10-03 主动触发接口

```text
POST /api/v1/applications/{application_id}/conversation/proactive-query
```

请求体为 `{ "conversation_id": "uuid" }`。该动作由前端在 HR 进入当前会话后调用，GET 消息接口保持只读。返回数据包含 `conversation_id`、可选 `agent_turn` 和 `new_messages`；没有可提问条件时三者分别返回会话 ID、`null`、空数组。

AgentTurn 允许主动轮次没有 `source_message_id`，使用唯一幂等键 `application_id + conversation_id + goal_condition_signature`。主动轮次状态为 `processing → waiting/query_sent`，HR 消息进入后为 `goal_judgement`；解析失败为 `waiting/pending`，后续明确二元回答仍完成同一 query。

二元识别仅接受明确的“是/不是、对/不对、属于/不属于”等表达；额外说明不影响提取，混合肯定/否定和无法明确判断的回答保持待处理。判断只追加固定沟通消息，不更新 Application、Match 或投递状态。
