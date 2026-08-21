# 跨前后端业务事实基线

> 本文档是 Careerpass 当前跨前后端业务语义的唯一基线。它回答“用户是谁、可以做什么、系统产生什么业务结果、必须遵守哪些业务规则”，不定义 API、数据库、代码或页面实现。
>
> 前端产品文档是事实候选来源；后端文档、代码、迁移和测试分别负责实现承接与证据。事实提取和冲突处理遵循 [`business-fact-extraction.md`](business-fact-extraction.md)。

## 1. 基线范围和状态

### 1.1 当前产品定位

本项目是面向 VIP 用户进行核心功能和项目亮点演示的受控演示项目（Demo）。非演示环节不纳入当前开发范围，非核心功能遵循最小必要原则设计。

### 1.2 事实状态

| 状态 | 含义 |
| --- | --- |
| `confirmed` | 已确认，可作为前后端 Slice 的共同业务依据 |
| `derived` | 从来源归纳而来，尚未发现冲突，但尚未完成最终裁决 |
| `pending` | 存在冲突或缺失，影响范围内的 Slice 不得自行猜测 |
| `superseded` | 已被新的事实替代，仅保留追溯意义 |

当前 Slice 默认只使用 `confirmed` 事实。

## 2. 来源索引

| 来源 | 提供的业务证据 |
| --- | --- |
| [`frontend-acceptance-flow.md`](../../careerpass-frontend/docs/product/frontend-acceptance-flow.md) | 角色、主流程、用户可观察结果、状态和交互规则 |
| [`frontend-product-flow.md`](../../careerpass-frontend/docs/product/frontend-product-flow.md) | 页面承载的业务动作、页面关系和用户可见结果 |
| [`frontend-development-decisions.md`](../../careerpass-frontend/docs/decisions/frontend-development-decisions.md) | 产品范围、非目标和已裁决的前端交互决策 |
| [`local-data-spec.md`](../../careerpass-frontend/docs/development/local-data-spec.md) | 对象关系、状态候选和主流程数据语义；固定值仅作来源证据 |

## 3. 角色和业务对象

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-ROLE-001` | `confirmed` | 求职者负责提供本人简历和其他求职资料、创建求职目标、启动求职 Agent，并查看本人的匹配、投递和求职进度结果。 |
| `BF-ROLE-002` | `confirmed` | HR 负责提供岗位 JD、查看授权范围内的投递和沟通信息，并更新当前岗位下当前候选人的投递进度。 |
| `BF-ROLE-003` | `confirmed` | 求职 Agent 是系统行为主体，不提供独立用户页面；其行为通过任务状态、匹配结果、投递记录和沟通状态体现。 |
| `BF-OBJECT-001` | `confirmed` | 简历是求职者进行解析、匹配和后续求职流程的基础资料。 |
| `BF-OBJECT-002` | `confirmed` | 其他求职资料用于保存证书等附加资料；当前业务语义不要求其进入简历解析流程。 |
| `BF-OBJECT-003` | `confirmed` | 岗位 JD 是 HR 提供的、可供后续岗位流程使用的岗位输入。 |
| `BF-OBJECT-004` | `confirmed` | 求职目标描述求职者希望达到的 Offer 数量、目标岗位和筛选条件；当前目标不绑定具体简历，当前版本每个求职者只验证一个当前目标。 |
| `BF-OBJECT-005` | `confirmed` | 投递记录表示一个候选人对一个岗位的一次投递。 |
| `BF-OBJECT-006` | `confirmed` | 沟通会话属于具体投递上下文，记录 HR 与求职 Agent 的系统内消息。 |
| `BF-OBJECT-007` | `confirmed` | 求职进度表示一条投递记录当前所处的招聘阶段，不是候选人或岗位的全局状态。 |
| `BF-OBJECT-008` | `confirmed` | Job 是一次岗位 JD 输入对应的独立岗位业务对象，由提交该 JD 的 HR 所有；不同内容形成相互独立的 Job。 |
| `BF-OBJECT-009` | `confirmed` | 结构化候选人画像是简历解析成功后的业务结果，用于求职目标、Agent 启动资格和岗位匹配；解析成功不必然表示画像具备匹配资格。 |
| `BF-OBJECT-010` | `confirmed` | 一个求职者可以拥有多份简历；每份简历对应一次独立的 PDF 输入和解析结果。 |
| `BF-OBJECT-011` | `confirmed` | 求职者资料是候选人拥有的附加文件资源，用于保存并供后续授权流程检索；不自动进入简历解析流程。 |
| `BF-OBJECT-012` | `confirmed` | 匹配结果是独立持久化的业务结果，作为岗位筛选和系统内投递的依据；投递记录不替代匹配结果。 |

## 4. 主流程和前置条件

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-FLOW-001` | `confirmed` | 标准演示流程为：HR 提供岗位 JD → 求职者登录并上传简历 → 简历解析成功 → 创建求职目标 → 启动 Agent → 查看投递进度 → HR 沟通并更新投递进度 → Offer 达到目标后 Agent 结束。 |
| `BF-FLOW-002` | `confirmed` | 求职者必须登录后才能进入求职者业务流程；HR 必须登录后才能进入 HR 业务流程。 |
| `BF-FLOW-003` | `confirmed` | 求职者可以在简历解析完成前创建或保存当前求职目标；该目标不能因此直接启动 Agent。 |
| `BF-FLOW-004` | `confirmed` | S-07 只有在当前求职目标已创建、当前简历解析成功且候选人画像具备岗位匹配资格时才具备启动条件；可用结构化岗位 JD 的检查归属 S-08。 |
| `BF-FLOW-005` | `confirmed` | 进入 S-08 匹配前必须存在至少一个可供当前演示使用的岗位 JD；S-07 启动 Agent 不依赖该条件。 |
| `BF-FLOW-006` | `confirmed` | Offer 数量达到求职目标中的目标数量，或本轮全部可用岗位均已筛选完成且本轮 Application 数量为 0 时，当前 Agent 运行结束。 |
| `BF-FLOW-007` | `confirmed` | Agent 已启动后，本轮全部可用岗位均已筛选完成且没有生成投递记录时，业务结果为“当前没有可供匹配的岗位”，不得使用虚构岗位填充。 |
| `BF-FLOW-008` | `confirmed` | 岗位流程中，S-02 负责上传 JD、建立 Job 并交接解析任务；S-03 负责真实解析并形成结构化 JD 快照；S-08 只消费结构化 JD 快照进行匹配。S-02 的上传成功不等同于 JD 解析成功。 |
| `BF-FLOW-009` | `confirmed` | 受控演示中的岗位 JD 上传只接受 Markdown（`.md`）文件；HR 选择一份或多份文件后立即提交上传，不需要额外确认按钮。 |
| `BF-FLOW-010` | `confirmed` | 当前受控演示中，一份 Markdown 文件对应一份岗位 JD；JD 使用固定标题提取字段，除岗位名称、工作地点、薪资、岗位职责和任职要求外可以包含其他固定标题。 |
| `BF-FLOW-011` | `confirmed` | 求职者正式简历只接受 PDF 文件；当前版本不处理扫描件、图片型 PDF、加密 PDF 或密码保护 PDF。 |
| `BF-FLOW-012` | `confirmed` | 岗位 JD 删除成功后，该岗位从当前可用岗位列表移除；没有其他可用岗位时展示岗位空状态。 |
| `BF-FLOW-013` | `confirmed` | 求职者一次只能上传一份 PDF 简历；重复上传相同内容时复用已有简历结果，不创建新版本或新的解析任务。 |
| `BF-FLOW-014` | `confirmed` | 求职者登录后可以一次选择一份或多份附加资料手动上传；批次按文件独立处理，单个文件失败不影响同批次已成功文件。 |
| `BF-FLOW-015` | `confirmed` | 附加资料上传后，前端显示逐文件结果并在资料列表中提供名称、文件格式、上传时间和上传状态等展示所需信息；具体响应字段由 Integration Contract 定义。 |
| `BF-FLOW-016` | `confirmed` | S-06 求职目标配置可以与 S-02/S-03 岗位准备和 S-04 简历解析并行；简历和画像条件由 S-07 校验，岗位 JD 条件由 S-08 在匹配前校验。 |
| `BF-FLOW-017` | `confirmed` | S-07 只负责校验启动条件、绑定启动时有效的当前简历、创建本轮运行上下文并使 Agent 进入运行中；匹配和投递记录由 S-08 负责。 |
| `BF-FLOW-018` | `confirmed` | S-07 启动事务提交后，后端同步执行 S-08 的岗位筛选、匹配结果持久化和通过岗位的系统内投递；前端不再次提交匹配命令，也不展示匹配过程。 |

## 5. 跨角色业务规则

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-RULE-001` | `confirmed` | 未登录用户不能进入求职者或 HR 业务页面。 |
| `BF-RULE-002` | `confirmed` | 求职者和 HR 只能看到各自角色允许的页面和业务结果；一个角色的页面菜单不代表另一个角色的访问权限。 |
| `BF-RULE-003` | `confirmed` | 用户选择的工作区身份必须与服务端确认的身份一致；前端选择不能单独形成后端授权事实。 |
| `BF-RULE-004` | `confirmed` | 简历需要进入解析流程；其他求职资料当前只保存并展示上传就绪结果，不进入简历解析流程。 |
| `BF-RULE-005` | `confirmed` | Agent 运行中不能替换当前投递轮次绑定的简历；更换简历不能修改历史投递。 |
| `BF-RULE-006` | `confirmed` | Agent 结束后历史投递继续保留，当前任务不能再次启动。 |
| `BF-RULE-007` | `confirmed` | 一条投递记录只允许在其所属岗位和候选人关系范围内被更新；HR 不得借此修改候选人或岗位的全局状态。 |
| `BF-RULE-008` | `confirmed` | 沟通完整消息记录只在 HR 授权范围内展示；求职者侧不展示单个岗位的完整聊天内容，只展示业务允许的沟通状态。 |
| `BF-RULE-009` | `confirmed` | 当前版本的匹配、投递和沟通只在系统内演示或记录，不向真实招聘平台或真实招聘方产生外部副作用。 |
| `BF-RULE-010` | `confirmed` | 异步操作或消息发送期间不能重复提交；失败时必须保留必要输入并提供可理解的重试反馈。 |
| `BF-RULE-011` | `confirmed` | 同一 HR 对同一 JD 内容的未删除 Job 重复上传时，返回既有 Job 的幂等成功结果，不重复创建 Job 或解析任务；内容不同则创建独立 Job；已删除 Job 不参与复用，重新上传按全新 Job 处理。 |
| `BF-RULE-012` | `confirmed` | 简历具备正式岗位匹配资格必须同时满足：姓名可解析、简历中存在手机号或邮箱、教育经历有效，且工作经历或项目经历至少一项有效；年龄缺失不影响匹配资格。联系方式必须直接来自简历，不能由账户资料补足。 |
| `BF-RULE-013` | `confirmed` | 简历上传成功且解析成功不等于具备匹配资格；缺少 `BF-RULE-012` 任一必需业务字段时，简历标记为不可匹配，且不得启动 Agent；当前简历上传页只展示上传和解析处理结果，不展示画像字段或匹配资格详情。 |
| `BF-RULE-018` | `confirmed` | 姓名、手机号或邮箱、教育经历，以及工作经历或项目经历至少一项，是简历画像的最小业务字段；目标岗位、技能、工作年限、期望地点和期望薪资等字段均为可选字段，缺失不阻断解析成功。 |
| `BF-RULE-019` | `confirmed` | 工作年限只按具有有效起止年月的非实习工作经历计算，重叠月份不重复累计，“至今”取解析发生时的真实年月；不足一年返回整数月，满一年后按月份四舍五入为整数年（6 个月进位），所有工作经历均无有效时间段时返回 `unknown`。 |
| `BF-RULE-020` | `confirmed` | 附加资料只接受 PDF、Markdown、JPG 和 PNG 文件，单个文件大小不得超过 10 MB；格式不支持或大小超限的文件进入上传失败结果。 |
| `BF-RULE-021` | `confirmed` | 同一求职者重复上传同一附加资料时返回既有资料的幂等成功结果，不重复创建业务资料；具体幂等请求字段由 Integration Contract 定义。 |
| `BF-RULE-022` | `confirmed` | 附加资料的上传和创建归属 S-05，资料删除归属 S-11；S-05 不实现删除行为。 |
| `BF-RULE-023` | `confirmed` | S-05 不主动向后续沟通流程或 HR 暴露附加资料原文件；后续 Agent 检索到相关资料后，按授权流程将其交给 S-10 使用。 |
| `BF-RULE-024` | `confirmed` | Agent 尚未启动时，求职者可以更新同一个当前求职目标；Agent 运行中或已结束后，当前目标不可修改；当前版本不创建并行目标。 |
| `BF-RULE-025` | `confirmed` | 求职目标创建时不绑定简历；点击启动 Agent 时，由 S-07 将当时有效的当前简历绑定到本轮 Agent/投递运行上下文，运行中不得替换该绑定。 |
| `BF-RULE-026` | `confirmed` | 求职目标的 Offer 数量必须为 1 至 10 的正整数；岗位名称必填；筛选条件可为空并按自由文本保存。 |
| `BF-RULE-027` | `confirmed` | 求职目标保存是当前目标的创建或更新，不是 Agent 启动提交；重复保存不得产生第二个当前目标，Agent 启动由 S-07 独立负责。 |
| `BF-RULE-028` | `confirmed` | 同一当前 Agent 运行上下文收到重复启动请求时按幂等成功处理，不创建新的运行上下文；运行中或已结束的任务不得再次开启新运行。 |
| `BF-RULE-029` | `confirmed` | Agent 进入运行中后，求职目标仍保持其原有业务状态，但编辑权限被冻结；目标状态只有在后续流程达到 Offer 目标时才转为 `achieved`。 |
| `BF-RULE-014` | `confirmed` | JD 的岗位名称、工作地点、薪资、岗位职责和任职要求是当前岗位匹配所需的最小业务语义；当前构造数据保证这些字段有效，额外固定标题不改变五项核心字段的准入判断。 |
| `BF-RULE-015` | `confirmed` | 当前版本使用不依赖外部服务的简化岗位匹配；本轮允许全部可用岗位均未通过投递筛选，形成零 Application 的正常结果；不实现匹配服务失败分支。 |
| `BF-RULE-016` | `confirmed` | 岗位 JD 处于解析中或已开始匹配时，前端删除操作必须禁用并显示原因；服务端仍必须独立复核删除条件。 |
| `BF-RULE-017` | `confirmed` | 岗位 JD 删除不展示为用户可见的业务时间线事件，但删除结果必须保留最小审计信息；审计不得包含 JD 正文、对象定位或原始异常。 |
| `BF-RULE-030` | `confirmed` | 当前版本对本轮可用岗位逐个执行筛选；通过匹配与投递筛选的岗位创建系统内投递记录，不采用只投递一批中 Top-N 岗位的策略。 |
| `BF-RULE-031` | `confirmed` | 求职目标中的 `offer_target` 只表示目标 Offer 数量，与本轮岗位筛选数量和投递数量完全解耦。 |
| `BF-RULE-032` | `confirmed` | S-08 的匹配输入只能使用已解析并校验的岗位 JD 业务语义摘要和候选人简历业务语义摘要，不直接使用 JD 原文、简历原文或模型原始响应。 |
| `BF-RULE-033` | `confirmed` | 同一 Agent 运行上下文中，同一岗位 JD 只允许被筛选一次；重复触发或任务重试不得重复筛选、重复生成该岗位的有效结果或重复创建投递记录。 |
| `BF-RULE-034` | `confirmed` | 求职者求职进度页当前只展示已创建的投递记录及其进度；未通过投递筛选、未形成投递记录的匹配结果不在该页面展示。 |
| `BF-RULE-035` | `confirmed` | S-08 只使用岗位名称、工作地点、薪资、岗位职责和任职要求五项核心 JD 业务字段；公司简介、优先条件、加分项及其他非核心内容不解析，不进入过滤、匹配评分或推荐理由。 |
| `BF-RULE-036` | `confirmed` | 当本轮全部可用岗位均已筛选完成且本轮 Application 数量为 0 时，Agent 以“没有可供匹配的岗位”结束；该结束条件不要求 Offer 数量达到目标。 |
| `BF-RULE-037` | `confirmed` | 求职进度页展示已创建 Application 对应的推荐匹配得分和推荐理由；未形成 Application 的 Match 不展示。 |
| `BF-RULE-038` | `confirmed` | 当前演示候选人的匹配候选集为关联 HR 已上传且可用的全部结构化岗位 JD；演示只设置一个 HR 与一个 Candidate，不单独实现跨 HR 授权筛选。 |
| `BF-RULE-039` | `confirmed` | HR 投递进度页只展示岗位名称、公司名称、候选人姓名和当前投递进度；Application、Job 等内部标识可用于接口操作，但不作为页面业务信息展示。 |
| `BF-RULE-040` | `confirmed` | 当前演示中，HR 查询当前 HR 所有未删除岗位下的当前首轮 Application；单 Candidate 受控演示以全局最新 AgentRunContext 作为当前首轮，不纳入历史 Candidate 的旧运行；不实现多候选人、多轮投递、历史轮次、跨 HR 查询或独立岗位授权配置。 |
| `BF-RULE-041` | `confirmed` | HR 更新必须作用于当前 HR 有权访问的单条 Application，并同时校验 Job 归属、Candidate 关系和 Application 关系；不得仅凭 Application ID 授权。 |
| `BF-RULE-042` | `confirmed` | Application 状态更新只能向后推进或进入 `terminated`；同状态重复提交按幂等成功处理且不新增 ProgressEvent；非法回退和终态修改失败且保持原状态。 |
| `BF-RULE-043` | `confirmed` | Application 进入 `offer` 后，系统统计当前首轮 AgentRun 的 Offer 数量；达到 `offer_target` 时，AgentRun 进入 `finished`、结束原因为 `offer_target_reached`，当前 JobGoal 转为 `achieved`。 |
| `BF-RULE-044` | `confirmed` | AgentRun 因 Offer 达标结束后，当前轮次其它未终态 Application 仍允许 HR 按合法状态机继续推进；AgentRun 不得重新启动，已进入终态的 Application 不得修改。 |
| `BF-RULE-045` | `confirmed` | S10 的系统内沟通只作用于当前 Application 对应的 Conversation，Agent 是主动消息和回答消息的业务发送主体，不产生真实外部招聘沟通。 |
| `BF-RULE-056` | `confirmed` | S-08 为成功创建的系统内 Application 幂等初始化唯一 Conversation 容器；当前版本不自动写入欢迎消息，首条业务消息由 HR 提问产生。 |
| `BF-RULE-046` | `confirmed` | S10-01 只支持经历、项目和技能等简历相关问题；回答以 S-07 启动时绑定的 Resume 直接事实为准，CandidateProfile 只能作为其结构化投影，当前 Conversation 历史只作上下文；回答可提及项目名称，不向 HR 展示完整简历、原文片段或证据摘要。 |
| `BF-RULE-047` | `confirmed` | S10-01 检索、生成或校验失败但消息通道可用时发送受控模板；消息发送有限重试仍失败时不追加回复；同一请求重试复用已有回答。 |
| `BF-RULE-048` | `confirmed` | S10-02 的资料请求仅限当前 Candidate 的其它求职资料；当前投递会话默认可使用 CandidateDocument，不设置候选人二次授权，但仍须校验当前候选人归属和投递上下文；同一 CandidateDocument 可被多个 Application 的 Conversation 复用。 |
| `BF-RULE-049` | `confirmed` | S10-02 将资料作为一条 Agent 消息关联一个 MessageAttachment 交付；匹配成功时不显示“已为你找到”等额外成功提示语，前端只展示仿微信接收文件效果的附件卡片；HR 可以重复下载，但当前演示不提供在线预览或文件内容查看能力；附件只展示文件名、格式、大小和必要时间信息，创建后 7 天内有效。 |
| `BF-RULE-050` | `confirmed` | S10-02 重复发送按幂等处理；附件准备或消息发送失败有限重试仍失败时不产生可见 Agent 消息或半成品附件；未找到或资料失效时返回友好受控消息；成功交付保留不可见的最小审计记录，且不改变 Application 状态。 |
| `BF-RULE-057` | `confirmed` | S10-02 只基于 CandidateDocument 文件名进行确定性语义匹配，使用标准化和受控关键词/别名，不读取文件内容、不进行 OCR/Embedding、不调用 LLM；每次资料请求最多交付一个资料，主演示 Fixture 保证只有一个符合项。 |
| `BF-RULE-051` | `confirmed` | S10-03 主动获取的信息来自 JobGoal 求职过滤条件；已在岗位匹配/筛选阶段完成判断的条件不再询问，未处理条件通过语义识别形成待核验条件。岗位条件不限定为“是否外包”；该条件仅是当前受控演示可使用的示例。 |
| `BF-RULE-052` | `confirmed` | HR 进入当前 Application Conversation 后，S10-03 默认自动触发。对未被筛选阶段处理且无法由 JD 确认的条件，Agent 只生成一个 query 并写入当前 Conversation；没有可提问条件时静默结束，不发送消息。 |
| `BF-RULE-053` | `confirmed` | S10-03 只从 HR 回复中识别明确的二元表达，包括“是/不是”“对/不对”“属于/不属于”等常见表述；回复带额外说明时只提取其中的二元答案。识别为不继续推进时回复“感谢沟通，当前不考虑这个岗位了”；识别为继续推进时回复“好的，了解”。同时包含肯定和否定、或无法明确判断的回答不纳入当前业务范围。 |
| `BF-RULE-054` | `confirmed` | 在 HR 回复前 Agent 不主动追问并保持等待；HR 回复但未识别到明确二元答案时，视为没有有效回复，query 保持待处理，不发送额外提示，不作继续或停止判断。解析失败后 HR 再次发送明确二元答案时，仍视为对原 query 的有效回答。 |
| `BF-RULE-055` | `confirmed` | S10-03 根据同一 Conversation 历史判断是否已触发和处理：同一未确认条件最多发送一次 query，重复进入或重复触发不重复发送；有效二元回答完成判断后不再继续发起其它 query。判断结果只服务于当前 Conversation 和后续沟通行为，不修改 Application、匹配结果或其它投递状态。 |
| `BF-RULE-058` | `confirmed` | S-11 对简历、附加资料和岗位 JD 统一执行逻辑移除：资源从当前可用列表和后续业务检索中移除，物理文件仅在没有有效引用后按对象清理规则处理；当前版本不提供回收站或恢复入口。 |
| `BF-RULE-059` | `confirmed` | 简历仅在解析任务进入 `succeeded` 或 `failed` 终态且 Agent 尚未启动时允许逻辑移除；`processing`、Agent 运行中和 Agent 已结束时不得移除。`matching_ready` 或 `matching_not_ready` 不改变删除资格。 |
| `BF-RULE-060` | `confirmed` | 一个求职者可以拥有多份简历；Agent 尚未启动时，新上传的不同内容简历自动成为当前简历，解析未完成时仍不能启动 Agent；Agent 启动后当前简历绑定，不允许替换或移除。S-11 的前端删除操作只针对当前简历。 |
| `BF-RULE-061` | `confirmed` | 附加资料成功保存后可在 Agent 未启动、运行中或已结束时逻辑移除；移除后不得用于新的资料检索，已经创建的 `MessageAttachment` 在 7 天有效期内继续可下载。 |
| `BF-RULE-062` | `confirmed` | 已逻辑移除的附加资料不参与重复上传幂等判断；相同内容再次上传时创建新的业务资料。删除先于资料检索提交时不得创建新附件，附件创建先于删除提交时不影响其有效期内下载。 |
| `BF-RULE-063` | `confirmed` | 简历、附加资料和岗位 JD 的删除均保留最小审计记录；审计记录不包含删除原因、文件正文、联系方式、对象定位或原始异常。重复删除按幂等结果处理，不重复产生删除事件。 |

## 6. 智能体和投递状态

### 6.1 智能体生命周期

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-STATE-001` | `confirmed` | Agent 生命周期包含“未启动”“可启动”“运行中”“已结束”四类业务状态。 |
| `BF-STATE-002` | `confirmed` | S-07 的“可启动”条件是求职目标已创建、当前简历解析成功且候选人画像具备岗位匹配资格；可用结构化岗位 JD 不属于 S-07 启动条件，由 S-08 在匹配前检查。 |
| `BF-STATE-003` | `confirmed` | 用户启动后 Agent 进入“运行中”；运行中不能替换当前简历，也不能重复启动当前任务。 |
| `BF-STATE-004` | `confirmed` | Offer 数量达到目标，或本轮全部可用岗位已筛选完成且 Application 数量为 0 后，Agent 进入“已结束”；已结束任务不能再次启动。 |
| `BF-STATE-009` | `confirmed` | 简历解析状态与岗位匹配资格分开表达：解析可以成功但画像不可匹配；不可匹配状态阻断 Agent 启动，年龄缺失不触发该状态。 |
| `BF-STATE-014` | `confirmed` | 简历解析主路径为 `processing → succeeded` 或 `processing → failed`；解析成功后另行计算 `matching_ready` 或 `matching_not_ready`，二者不互相替代。 |
| `BF-STATE-015` | `confirmed` | 附加资料上传状态为：用户点击上传至文件完成数据存储前为 `ready`，数据存储成功后为 `success`；文件格式不支持或大小超限时为 `failed`。 |
| `BF-STATE-016` | `confirmed` | 求职目标状态包含 `active`、`achieved` 和 `abandoned`；S-06 创建或更新当前目标时使用 `active`，Offer 数量达到目标后由后续求职流程转为 `achieved`；当前版本没有用户主动放弃入口。 |
| `BF-STATE-017` | `confirmed` | S-07 启动成功后的用户可观察状态为 Agent“运行中”；启动页面不展示匹配资格详情，未满足条件时统一表现为尚未启动/暂不可启动。 |
| `BF-STATE-018` | `confirmed` | `matching_ready` 表示解析成功且姓名、简历内手机号或邮箱、有效教育经历，以及工作经历或项目经历至少一项齐全；`matching_not_ready` 表示解析成功但缺少至少一项必需字段。二者都属于解析完成，只有前者满足 Agent 启动的匹配资格条件。 |

### 6.2 投递进度状态

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-STATE-005` | `confirmed` | 投递进度状态依次表达 `submitted`（已投递）、`screening`（初筛中）、`written_test`（笔试）、`interview_1`（一面）、`interview_2`（二面）、`interview_3`（三面）、`hr_interview`（HR 面）、`offer`（获得 Offer）和 `terminated`（流程终止）。 |
| `BF-STATE-006` | `confirmed` | `offer` 和 `terminated` 是终态；进入终态后不能再次修改。 |
| `BF-STATE-007` | `confirmed` | 非终态投递记录可以向后跳转到时间轴后方的阶段，也可以进入 `terminated`；不允许回退到更早阶段。时间轴展示顺序不表示每个岗位必须经历全部阶段。 |
| `BF-STATE-008` | `confirmed` | `terminated` 在当前版本统一表达为“流程终止”，不能在不同页面无说明地改写为其他业务语义。 |
| `BF-STATE-010` | `confirmed` | 岗位 JD 解析状态与匹配资格分开表达：只有形成五项核心字段均有效的 `fields` 才进入 `parse_succeeded + matching_ready`；核心字段缺失进入 `parse_failed + matching_not_ready`，不生成可供 S-08 使用的快照。 |
| `BF-STATE-011` | `confirmed` | 当前 S-03 异步失败只定义三种失败语义：临时技术失败（自动重试，耗尽后终止）、输入不可用（立即终止）、核心字段缺失（立即终止且不保留快照）；当前受控演示不纳入结构校验失败分支。 |
| `BF-STATE-012` | `confirmed` | 岗位 JD 只有在解析任务进入 `succeeded` 或 `failed` 终态后才进入删除资格判断；处于 `queued` 或 `running` 时不可删除。 |
| `BF-STATE-013` | `confirmed` | “匹配已开始”由 S-08 的匹配发起事实提供；当前受控演示可使用后端拥有的模拟状态语义，但客户端不得自行提交该事实。 |

## 7. 当前版本范围和非目标

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-SCOPE-001` | `confirmed` | 当前版本只验证求职者和 HR 共同参与的、可重复演示的系统内求职核心闭环。 |
| `BF-SCOPE-002` | `confirmed` | 当前版本不把公开注册、复杂账号体系、多租户、真实外部投递、真实外部消息、多轮投递、实时推送和生产级平台能力作为核心演示范围。 |
| `BF-SCOPE-003` | `confirmed` | 非演示环节不纳入当前开发范围；非核心功能按最小必要原则设计。 |
| `BF-SCOPE-004` | `confirmed` | 当前版本只验证一个当前求职目标和首轮投递流程，不要求多目标、多轮投递或多份简历并行管理。 |
| `BF-SCOPE-005` | `confirmed` | 当前版本的账号以受控演示账号为主，不因页面存在注册入口就自动纳入公开注册能力。 |
| `BF-SCOPE-006` | `confirmed` | 前端 Mock 数据的固定 ID、用户名、密码、展示名称、岗位样本和消息文本不是跨前后端业务事实。 |
| `BF-SCOPE-007` | `confirmed` | 岗位 Job 只有在 JD 解析任务进入终态且岗位匹配流程尚未开始时允许逻辑移除；`queued/running` 或一旦发起匹配流程，不得再移除该 Job。简历和附加资料的 S-11 删除范围由 `BF-RULE-058` 至 `BF-RULE-063` 定义。 |
| `BF-SCOPE-008` | `confirmed` | 当前版本将 JD 真实结构化解析放在 S-03；S-02 只负责上传、建立 Job 和解析任务交接，S-08 消费 S-03 形成的结构化 JD 快照。 |
| `BF-SCOPE-009` | `confirmed` | 岗位 JD 内容不同即形成相互独立的 Job；同一 HR 对同一内容的未删除 Job 重复上传返回既有 Job 的幂等成功结果；已删除 Job 不复用，重新上传创建新 Job；当前版本不定义 Job 覆盖、版本链或 current/latest 语义，也不验收跨 HR 同内容和并发重复上传。 |
| `BF-SCOPE-010` | `confirmed` | 解析失败的 Job 再次上传相同 JD 内容时，若原 Job 未删除则复用原 Job 并重建解析任务；若原 Job 已删除则不得复用，必须创建新 Job；内容不同也创建新 Job。 |
| `BF-SCOPE-011` | `confirmed` | 当前版本只验证 PDF 文本型正式简历；其他简历格式、扫描件、图片型 PDF、加密 PDF 和密码保护 PDF 不在当前版本范围内。 |
| `BF-SCOPE-012` | `confirmed` | 当前演示岗位 JD 使用构造的 Markdown 数据，一份文件对应一份 Job；主路径数据保证五项核心字段有效。核心字段缺失按 `BF-STATE-010` 形成不可匹配状态，但不作为主路径验收内容。 |
| `BF-SCOPE-013` | `confirmed` | 当前版本的岗位匹配使用本地简化算法，不依赖外部匹配服务；匹配结果独立持久化，但求职进度页只展示其中已形成投递记录的结果；本轮 Application 数量可以为 0。 |
| `BF-SCOPE-018` | `confirmed` | 当前演示岗位池最多包含 20 个可用结构化岗位 JD；同步执行边界只适用于该受控规模。 |
| `BF-SCOPE-019` | `confirmed` | 当前演示不实现多 HR、多 Candidate 或独立岗位授权配置；一个 HR 与一个 Candidate 的场景下，S-08 使用该 HR 上传的全部可用岗位。 |
| `BF-SCOPE-014` | `confirmed` | 当前 S-03 只处理临时技术失败、输入不可用和核心字段缺失三种失败语义；结构清晰的演示 JD 不验收结构校验失败。 |
| `BF-SCOPE-015` | `confirmed` | 岗位 JD 删除成功后不保留可供当前业务读取的 S-03 解析快照；已删除 Job 不再作为当前岗位输入，也不参与相同内容的重复上传复用。 |
| `BF-SCOPE-016` | `confirmed` | S-04 内部能力验证使用固定 PDF；简历核心解析、真实异步解析链路和前端完整流程分层验证，不以任一层结果冒充其它层结果。 |
| `BF-SCOPE-017` | `confirmed` | S-05 只覆盖附加资料的手动批量上传、逐文件结果和保存后列表展示；删除由 S-11 负责，原文件的后续授权检索和沟通使用由后续流程负责。 |

## 8. 业务事实使用边界

- `confirmed` 事实是前端、后端和 Slice Design 的共同业务依据；
- `pending` 事实不能被 Coding Agent 通过技术实现自行裁决；
- 业务基线不定义 API 路径、响应字段、表结构、类名、方法名、异步框架或视觉细节；
- 后端领域模型可以把业务对象落地为实体、值对象或运行时投影，但必须保持本基线定义的业务语义；
- 前端可以用 Mock 数据演示本基线定义的业务状态，但 Mock 数据本身不构成后端资源、持久化事实或权限事实；
- 具体 Slice 只能细化本基线未明确的局部业务内容，不能静默改变已确认事实。

## 9. 待裁决事项处理

| 事项 | 当前状态 | 影响 | 裁决位置 |
| --- | --- | --- | --- |
| 当前业务裁决事项 | `confirmed` | S-08、S-09、S10-03 和 S-11 当前业务事项已完成裁决；S-11 的三类资源逻辑移除、简历当前绑定、附加资料检索和附件保留规则由本基线定义，接口与实现细节由对应 Slice 文档锁定 | [`matching-algorithm-v0.1.md`](matching/matching-algorithm-v0.1.md)；S-08/S-09/S10-03/S-11 Slice 文档 |

待裁决事项只阻塞受其影响的 Slice，不阻塞已经使用 `confirmed` 事实且业务边界独立的 Slice。
