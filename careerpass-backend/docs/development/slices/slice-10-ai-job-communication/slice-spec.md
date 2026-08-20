# Slice：S10 AI 求职沟通

> 当前状态：S10-01 已完成 Verify/Close 并标记为 `integration_delivered`；S10-02 核心能力已完成 Implement/Verify，但补充真实前端复测发现成功提示语和附件卡片展示问题，当前回退为 `integration_blocked`，待整改回归；S10-03 保持设计状态。
>
> 本文档只记录业务范围和业务规则，不定义 API、数据库、类、方法或具体 Tool。跨端场景地图见 [`../../../../docs/integration/slices/slice-10-ai-job-communication/delivery-map.md`](../../../../docs/integration/slices/slice-10-ai-job-communication/delivery-map.md)。
>
> Integration Scenario：[`IS-S10-01`](../../../../docs/integration/slices/slice-10-ai-job-communication/integration-scenario.md)、[`IS-S10-02`](../../../../docs/integration/slices/slice-10-ai-job-communication/integration-scenario-s10-02.md)；Integration Contract：[`IC-S10-AI-COMMUNICATION@0.4`](../../../../docs/integration/slices/slice-10-ai-job-communication/integration-contract.md)。
>
> Technical Design：[`technical-design.md`](./technical-design.md)。
>
> 跨前后端已确认业务事实以 [`business-baseline.md`](../../../../docs/business/business-baseline.md) 中的 `BF-RULE-045` 至 `BF-RULE-057` 为准。

## 1. 目标

在已完成岗位匹配并建立当前投递沟通后，Agent 能在授权范围内基于候选人简历事实回答 HR 问题、交付其它求职资料，并根据求职目标主动获取 JD 缺失信息、判断岗位是否继续推进和调整当前沟通行为。

## 2. 输入

- 当前 HR 在当前 Application 对应沟通会话中发送的问题；
- S-07 启动时绑定的当前投递轮次 Resume；
- 由该 Resume 形成并校验的 CandidateProfile；
- 当前求职目标中的求职过滤条件；
- 当前岗位的受控结构化 JD 信息；
- 当前 Application 对应 Conversation 的历史消息，仅作为当前问题上下文。

当前已交付增量消费 S-08 已初始化的 Conversation 容器；S10-02 后端资料附件交付核心能力已完成，但展示整改待回归；S10-03 仍不进入当前代码实现。

## 3. 输出

- 基于 Resume 直接事实形成的 Agent 正式会话消息；
- 相关问题可以提及 Resume 中的项目名称；
- 检索、生成或校验失败但消息通道可用时，发送统一的自然语言模板回复；
- 消息发送失败且有限重试耗尽时，不追加回复，不提供人工兜底或外部手动重新发起。
- S10-02 的资料交付通过系统内消息附件提供下载能力，但当前演示不提供在线预览或文件内容查看能力。
- S10-03 在当前 Conversation 中发送唯一 query；根据 HR 二元回答形成继续推进或停止推进的沟通结果。

## 4. 前置条件

- HR 已登录，且服务端确认其对当前 Job、Candidate、Application 和 Conversation 的访问权限；
- 当前 Application 已完成岗位匹配并存在可用沟通会话；
- 当前投递轮次存在 S-07 启动时绑定的 Resume；
- Resume 和 CandidateProfile 可供当前业务读取。
- 当前求职目标和受控结构化 JD 可供 S10-03 读取。

## 5. 业务规则

### 5.1 事实来源与读取范围

- S10-01 只支持经历、项目、技能等简历相关问题；无关问题使用统一模板回复，不进入简历事实回答流程。
- Agent 始终使用 S-07 启动时绑定的 Resume；当前 S10 演示不处理候选人多份简历选择。
- CandidateProfile 只是绑定 Resume 的结构化投影，不能独立覆盖 Resume。
- Agent 可以读取当前 Application 对应 Conversation 的历史消息，但历史消息只作为上下文，不构成高于 Resume 的事实来源。
- 事实优先级为：绑定 Resume、CandidateProfile、当前 Conversation 历史消息、Agent 历史回答。
- Resume 与 CandidateProfile 或历史消息冲突时，以绑定 Resume 为准。

### 5.2 回答与可见性

- Agent 只允许基于 Resume 中的直接事实回答，不得根据常识、模型推断或历史 Agent 回复补造经历、项目或技能。
- HR 只看到 Agent 生成的回答，不展示完整简历、简历原文片段或证据来源摘要。
- 回答可以提及与问题相关的项目名称，因为项目名称属于 Resume 直接事实的一部分。
- 当前实现不向 Qwen 提供姓名、联系方式、地址、Resume 原文、内部文件定位或模型原始响应；这些敏感字段不得进入日志、追踪、错误响应或非必要验收产物。

### 5.3 无证据与失败

- 当绑定 Resume-derived 的工作/项目事实范围已建立，且存在性问题的目标能力未出现在该范围内时，Agent 可以给出受控否定结论，例如“从当前求职资料看，没有大模型训练相关经历”；该结论只表示当前已覆盖的经历范围，不外推未提供或未形成结构化事实的简历内容。
- Resume-derived 事实范围为空或不足、问题超出支持范围，或无法形成上述事实支持时，Agent 使用统一自然语言模板回复，不伪造确定答案。
- 检索、回答生成或结构化校验失败，但消息通道可用时，发送受控模板回复，例如“暂时无法回答当前问题”；具体文案由 Integration Contract/Fixture 锁定。
- 消息持久化或发送失败时只进行有限自动重试；重试耗尽后不追加模板消息，不提供人工兜底，不产生外部消息。
- 同一请求的重试复用已有回答，不重复追加 Agent 消息；语义相同但重新提交的问题不属于当前演示验收范围。

### 5.4 候选人其它求职资料交付（S10-02）

- HR 可以请求当前 Candidate 已成功保存的任意 CandidateDocument，不限制为证书、照片或证明。
- 当前投递会话默认可以使用当前 Candidate 的 CandidateDocument，不设置候选人二次授权；同一资料可被多个 Application 复用。
- 资料意图只通过 HR 消息和 CandidateDocument 文件名进行确定性语义匹配；使用文件名标准化、关键词和受控别名，不读取文件内容，不使用 OCR、Embedding 或 LLM。
- 每次请求最多交付一个资料；主演示 Fixture 保证每个请求只有一个符合项，不验收多命中选择。
- 成功请求产生一条 `content` 为空的 Agent 消息，并关联一个 `MessageAttachment`；用户可见内容只有附件，HR 只能下载，不能在线预览或查看文件内容。
- 附件只展示文件名、格式、大小和必要时间信息；附件自创建时间起 7 天有效，CandidateDocument 删除不影响有效期内的已发送附件。
- HR 不需要额外确认或重新登录即可重复下载；服务端每次仍校验当前 HR、Job、Application、Conversation、Message 和 Attachment 的归属链。
- 同一请求重复提交按幂等处理，复用已有 Agent 消息和附件；附件准备或消息发送失败有限重试仍失败时，不产生可见 Agent 消息或半成品附件。
- 未找到资料或资料失效时使用友好受控消息，不暴露真实文件状态、文件内容、内部路径或对象定位；这些异常不作为主演示关闭条件。
- 资料交付只影响当前 Application 对应 Conversation，不改变 Application 状态；成功交付保留不可见的最小审计记录。

### 5.5 主动补齐岗位信息并调整沟通行为（S10-03）

- 主动获取的信息来源于当前 JobGoal 的求职过滤条件；已经在岗位匹配/筛选阶段完成判断的条件不再主动获取。
- Agent 对未处理的过滤条件进行语义识别，并与当前受控 JD 信息对比；当前演示的受控 JD 不包含“是否外包”等岗位性质信息。
- 对未被筛选阶段处理且无法由 JD 确认的条件，当前演示只生成一个 query，并由 Agent 写入当前 Application 对应 Conversation。
- 当前演示的问题是二元问题，HR 回答按“是/否”处理，不验收模糊回答。
- HR 未回答时视为尚未回复，Agent 不主动追问；解析失败时不自动判断为继续或停止，不发送错误结论，query 保持待处理，技术层可进行有限重试。
- 判断为停止推进时，Agent 回复“感谢沟通，当前不考虑这个岗位了”；判断为继续推进时，Agent 回复“好的，了解”。
- 判断结果只服务于当前 Conversation 和后续沟通行为，不修改 Application、匹配结果或其它投递状态。
- 当前演示不处理多个未确认条件，也不在一个 query 完成后继续发起其它 query。

## 6. 范围 / 非目标

### 当前范围

- HR 在当前投递会话中提出简历相关问题；
- Agent 读取绑定 Resume、CandidateProfile 和当前会话历史；
- Agent 基于直接简历事实生成并追加正式会话回答；
- HR 在当前投递会话中请求候选人的其它求职资料；
- Agent 基于 CandidateDocument 文件名语义检索一个资料，并以一条 Agent 文本消息关联一个可下载附件交付，不提供在线预览；
- 资料附件自创建时间起 7 天有效，CandidateDocument 删除不影响有效期内的已发送附件；资料交付只影响当前 Conversation，不改变 Application 状态，并保留最小不可见审计记录；
- Agent 根据求职目标识别一个 JD 未覆盖的条件，在当前 Conversation 中主动提问；
- Agent 根据 HR 二元回答判断继续或停止推进，并发送对应沟通消息；
- 无证据、生成失败和发送失败的受控结果。

S10-01 已完成纵向交付；S10-02 核心纵向能力已完成，成功消息语义和附件卡片展示整改待回归；S10-03 主动 query 继续保留在后续 Slice。

### 非目标 / 延期

- 候选人多份简历选择和跨简历比较；
- 向 HR 展示完整简历、原文片段或证据摘要；
- 将历史 Agent 回答作为独立事实来源；
- 外部招聘平台或真实招聘方消息发送；
- HR 重复问题的语义去重和本场景专门验收；
- 多个未确认条件、连续主动发起多个 query 和复杂/模糊回答；
- 判断结果对 Application、匹配结果或其它投递状态的改变；
- HR 未回答时的主动催促。

## 7. 验收标准

- 对固定简历 Fixture 中有直接事实的问题，Agent 能生成与事实一致的回答；
- 回答可以正确提及相关项目名称，但不展示简历原文或证据摘要；
- 经历事实范围完整但目标能力未出现时，Agent 返回受控否定回答；资料范围不足或问题超出支持范围时使用统一模板，不生成虚构答案；
- 读取范围只包含当前 Application 的 Conversation 历史，不读取其它岗位、候选人或投递的会话；
- CandidateProfile 与 Resume 冲突时，回答遵循 Resume；
- 同一请求重试不重复追加 Agent 消息；
- 生成失败、校验失败和消息发送失败分别产生已裁决的结果；
- 失败结果不产生真实外部消息或未经授权的副作用。
- HR 请求其它求职资料时，Agent 能根据文件名语义返回一个可下载的系统内消息附件；成功时不返回额外提示语，当前演示不提供在线预览或文件内容查看。
- 一次资料请求产生一条 `content` 为空的 Agent 消息并关联一个附件；前端以仿微信接收文件效果展示文件名、格式、大小和必要时间信息。
- 附件自创建时间起 7 天有效；CandidateDocument 删除不影响有效期内的已发送附件；资料附件交付不改变 Application 状态，并产生最小不可见审计记录。
- Agent 能从未被岗位筛选阶段处理的求职过滤条件中识别一个 JD 缺口，并在当前 Conversation 中发送唯一 query。
- HR 以二元答案回复后，Agent 能形成继续推进或停止推进判断，并分别发送“好的，了解”或“感谢沟通，当前不考虑这个岗位了”。
- HR 未回答时 Agent 不主动追问；解析失败时不产生错误推进结论，query 保持待处理。
- S10-03 判断结果只影响当前 Conversation，不改变 Application、匹配结果或其它投递状态。

## 8. 开发者需裁决事项

### 已确认

- S10-01 上述业务事实已由开发者确认并完成交付；S10-02 业务事实已确认，核心能力已交付但展示整改尚未关闭；S10-03 仅保留后续设计事实。

### 已同步的交付事实

- S10-02 新增的成功消息“只显示附件、不显示额外提示语”和仿微信文件卡片展示事实已同步到业务基线、Integration Contract 和前端事实源；S-08 Conversation Handoff、S10-01 Contract、Qwen 真实能力证据、验收 Fixture、数据库/权限/幂等集成和前端演示均已记录并通过。
- S10-01 已完成 Slice Select、Slice Design、Readiness Check、Implement、Verify 和 Close；`IS-S10-01` 已裁定为 `integration_delivered`。
- S10-02 已完成业务裁决和核心代码交付：确定性文件名语义匹配、单资料交付、一条 `content` 为空的 Agent 消息关联一个附件、7 天有效期、删除后的独立下载、跨 Application 复用和无 LLM 内容读取；后端代码、迁移和核心联调已通过，但真实前端复测发现成功提示语和附件卡片展示问题，场景待整改回归。
