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
| `BF-OBJECT-004` | `confirmed` | 求职目标描述求职者希望达到的 Offer 数量、目标岗位和筛选条件；当前版本每个求职者只验证一个当前目标。 |
| `BF-OBJECT-005` | `confirmed` | 投递记录表示一个候选人对一个岗位的一次投递。 |
| `BF-OBJECT-006` | `confirmed` | 沟通会话属于具体投递上下文，记录 HR 与求职 Agent 的系统内消息。 |
| `BF-OBJECT-007` | `confirmed` | 求职进度表示一条投递记录当前所处的招聘阶段，不是候选人或岗位的全局状态。 |
| `BF-OBJECT-008` | `confirmed` | Job 是一次岗位 JD 输入对应的独立岗位业务对象，由提交该 JD 的 HR 所有；不同内容形成相互独立的 Job。 |

## 4. 主流程和前置条件

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-FLOW-001` | `confirmed` | 标准演示流程为：HR 提供岗位 JD → 求职者登录并上传简历 → 简历解析成功 → 创建求职目标 → 启动 Agent → 查看投递进度 → HR 沟通并更新投递进度 → Offer 达到目标后 Agent 结束。 |
| `BF-FLOW-002` | `confirmed` | 求职者必须登录后才能进入求职者业务流程；HR 必须登录后才能进入 HR 业务流程。 |
| `BF-FLOW-003` | `confirmed` | 求职者必须在简历解析成功后才能创建可用于启动流程的求职目标。 |
| `BF-FLOW-004` | `confirmed` | 求职 Agent 只有在简历解析成功且当前求职目标已创建时才具备启动条件。 |
| `BF-FLOW-005` | `confirmed` | 主流程开始前必须存在至少一个可供当前演示使用的岗位 JD。 |
| `BF-FLOW-006` | `confirmed` | Offer 数量达到求职目标中的目标数量后，当前 Agent 运行结束。 |
| `BF-FLOW-007` | `confirmed` | Agent 已启动但尚未生成投递记录时，业务结果是明确的空状态，不得使用虚构岗位填充。 |
| `BF-FLOW-008` | `confirmed` | 岗位流程中，S-02 负责上传 JD、建立 Job 并交接解析任务；S-03 负责真实解析并形成结构化 JD 快照；S-08 只消费结构化 JD 快照进行匹配。S-02 的上传成功不等同于 JD 解析成功。 |
| `BF-FLOW-009` | `confirmed` | 受控演示中的岗位 JD 上传只接受 Markdown（`.md`）文件；HR 选择一份或多份文件后立即提交上传，不需要额外确认按钮。 |

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

## 6. 智能体和投递状态

### 6.1 智能体生命周期

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-STATE-001` | `confirmed` | Agent 生命周期包含“未启动”“可启动”“运行中”“已结束”四类业务状态。 |
| `BF-STATE-002` | `confirmed` | “可启动”的业务条件是简历解析成功且求职目标已创建。 |
| `BF-STATE-003` | `confirmed` | 用户启动后 Agent 进入“运行中”；运行中不能替换当前简历，也不能重复启动当前任务。 |
| `BF-STATE-004` | `confirmed` | Offer 数量达到目标后 Agent 进入“已结束”；已结束任务不能再次启动。 |

### 6.2 投递进度状态

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-STATE-005` | `confirmed` | 投递进度状态依次表达 `submitted`（已投递）、`screening`（初筛中）、`written_test`（笔试）、`interview_1`（一面）、`interview_2`（二面）、`interview_3`（三面）、`hr_interview`（HR 面）、`offer`（获得 Offer）和 `terminated`（流程终止）。 |
| `BF-STATE-006` | `confirmed` | `offer` 和 `terminated` 是终态；进入终态后不能再次修改。 |
| `BF-STATE-007` | `confirmed` | 非终态投递记录可以向后跳转到时间轴后方的阶段，也可以进入 `terminated`；不允许回退到更早阶段。时间轴展示顺序不表示每个岗位必须经历全部阶段。 |
| `BF-STATE-008` | `confirmed` | `terminated` 在当前版本统一表达为“流程终止”，不能在不同页面无说明地改写为其他业务语义。 |

## 7. 当前版本范围和非目标

| 编号 | 状态 | 事实 |
| --- | --- | --- |
| `BF-SCOPE-001` | `confirmed` | 当前版本只验证求职者和 HR 共同参与的、可重复演示的系统内求职核心闭环。 |
| `BF-SCOPE-002` | `confirmed` | 当前版本不把公开注册、复杂账号体系、多租户、真实外部投递、真实外部消息、多轮投递、实时推送和生产级平台能力作为核心演示范围。 |
| `BF-SCOPE-003` | `confirmed` | 非演示环节不纳入当前开发范围；非核心功能按最小必要原则设计。 |
| `BF-SCOPE-004` | `confirmed` | 当前版本只验证一个当前求职目标和首轮投递流程，不要求多目标、多轮投递或多份简历并行管理。 |
| `BF-SCOPE-005` | `confirmed` | 当前版本的账号以受控演示账号为主，不因页面存在注册入口就自动纳入公开注册能力。 |
| `BF-SCOPE-006` | `confirmed` | 前端 Mock 数据的固定 ID、用户名、密码、展示名称、岗位样本和消息文本不是跨前后端业务事实。 |
| `BF-SCOPE-007` | `confirmed` | 岗位 Job 允许在岗位匹配流程开始前删除；一旦发起匹配流程，不得再删除该 Job。其他业务资料的删除范围不由本事实扩展定义。 |
| `BF-SCOPE-008` | `confirmed` | 当前版本将 JD 真实结构化解析放在 S-03；S-02 只负责上传、建立 Job 和解析任务交接，S-08 消费 S-03 形成的结构化 JD 快照。 |
| `BF-SCOPE-009` | `confirmed` | 岗位 JD 内容不同即形成相互独立的 Job；同一 HR 对同一内容的未删除 Job 重复上传返回既有 Job 的幂等成功结果；已删除 Job 不复用，重新上传创建新 Job；当前版本不定义 Job 覆盖、版本链或 current/latest 语义，也不验收跨 HR 同内容和并发重复上传。 |
| `BF-SCOPE-010` | `pending` | 解析失败的 Job 再次上传时，是否复用既有 Job、创建新 Job 或重新创建解析任务，属于 S-03 的解析失败与重试契约，S-02 不自行推断。 |

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
| 解析失败的 Job 再次上传语义 | `pending` | S-03 的失败、重试和 S-02 重复上传衔接 | S-03 Slice Design / Readiness Check |

待裁决事项只阻塞受其影响的 Slice，不阻塞已经使用 `confirmed` 事实且业务边界独立的 Slice。
