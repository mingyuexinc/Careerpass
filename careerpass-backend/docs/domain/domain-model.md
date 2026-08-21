# 后端领域模型

> 本文档只记录当前代码、迁移或已通过 Slice Design 确认的领域事实。状态和关系优先使用表格表达。
>
> 标记：`implemented` = 当前代码/迁移已确认；`slice-confirmed` = 当前 Slice 已确认、尚未完成实现；`deferred` = 当前版本不处理。

业务对象、角色关系和状态语义必须保持与项目级 [`../../../docs/business/business-baseline.md`](../../../docs/business/business-baseline.md) 一致；本文档只记录后端领域模型的技术落地事实。

## 1. 领域对象

| 对象 | 类型 | 所有者 | 职责 | 当前状态 | 来源/备注 |
| --- | --- | --- | --- | --- | --- |
| User | 持久化实体 | 无 | 认证账户，保存用户名和密码哈希 | `implemented` | 当前代码与迁移 |
| Candidate | 持久化实体 | User | 求职者业务身份 | `implemented` | 当前代码与迁移 |
| HrProfile | 持久化实体 | User | HR 业务身份 | `implemented` | S-01 领域与身份契约 |
| UserRole | 关联实体 | User | 记录可用 `candidate` / `hr` 角色 | `implemented` | 当前代码与迁移 |
| CurrentIdentity | 运行时投影 | 当前请求 | 提供 `user_id`、角色和可选业务身份 ID | `implemented` | 认证依赖；不持久化 |
| StoredFileObject | 持久化实体 | 业务资源引用 | 保存受控文件元数据和对象存储引用 | `implemented` | 不向公开 API 暴露内部定位 |
| Resume | 持久化实体 | Candidate | 保存正式简历和解析状态；同一 Candidate 可拥有多份简历；当前简历由 Agent 启动时绑定 | `implemented` | 当前代码与迁移；S-04 内容幂等规则；S-11 逻辑移除规则 |
| CandidateProfile | 持久化实体 | Resume | 保存成功解析后的结构化候选人画像，并提供独立的岗位匹配资格判定 | `implemented` | `resume_id` 一对一；解析成功不等于具备匹配资格 |
| CandidateDocument | 持久化实体 | Candidate | 保存附加求职资料，不进入解析状态机；上传业务状态由 S-05 负责；删除后不参与新的资料检索 | `implemented` | 当前代码与迁移；业务状态和 S-11 逻辑移除规则以业务基线为准 |
| AsyncTaskRun | 持久化实体 | 关联业务资源 | 保存异步任务权威状态、租约、幂等和脱敏失败分类 | `implemented` | 当前已支持简历解析；岗位任务由后续 Slice 扩展 |
| Job | 持久化实体 | HrProfile | 表示一份独立岗位，关联一个 JD 文件并作为 S-03 输入锚点 | `slice-confirmed` | S-02 已确认，代码/迁移待实现 |
| ParsedJobDescriptionSnapshot | 持久化实体 | Job | 保存 S-03 按固定 Markdown 标题解析并校验后的岗位结构化事实和展示字段 | `slice-confirmed` | 一份 Markdown 文件对应一个 Job；仅成功且五项核心字段有效时创建；不由 S-02 创建 |
| JobGoal | 持久化实体 | Candidate | 保存一个不绑定简历的当前求职目标；由 S-06 创建/更新，供 S-07 读取 | `implemented` | S-06 Slice Design、代码与迁移 |
| AgentRunContext | 持久化实体 | Candidate | 保存本轮 Agent 的目标快照、启动时绑定简历/画像和运行状态 | `slice-confirmed` | S-07 Slice Design；代码与迁移待实现 |
| Match | 持久化实体 | Candidate、Job、AgentRunContext | 保存本轮岗位筛选的独立结果、算法版本、输入快照、评分、状态和推荐理由 | `slice-confirmed` | S-08 Technical Design；`UNIQUE(run_id, job_id)` |
| Application | 持久化实体 | Candidate、Job、Match、AgentRunContext | 保存通过投递筛选后的系统内投递记录，初始为 `submitted` | `slice-confirmed` | S-08 Technical Design；一条 Application 只能关联一条 Match |
| ProgressEvent | 持久化实体 | Application | 记录 Application 创建和后续合法状态变化 | `slice-confirmed` | S-08 创建初始 `application_created` 事件；S-09 负责后续状态推进 |
| Conversation | 持久化实体 | Application | 当前投递上下文内的系统沟通会话 | `slice-confirmed` | S-10 Technical Design；一条当前 Application 对应当前 Conversation |
| Message | 持久化实体 | Conversation | HR 与 Agent 的系统内正式消息 | `slice-confirmed` | S-10 Technical Design；消息状态由 Conversation Message Service 拥有 |
| MessageAttachment | 持久化实体 | Message | CandidateDocument 在 Conversation 中的可下载附件投影；保留有效期内独立下载能力 | `implemented` | S10-02 迁移 `20260820_0016`、Repository 和下载接口；不提供在线预览；创建后 7 天有效 |
| ResourceAuditEvent | 持久化审计实体 | User/业务资源 | 保存三类业务资料删除的最小审计事件，不保存原因或敏感原值 | `implemented` | S-11 迁移与删除 Repository；资源类型、资源 ID、操作者、事件类型和时间唯一约束 |
| AgentTurn | 技术执行记录 | Conversation | Agent Turn 的幂等、执行状态和脱敏结果分类 | `slice-confirmed` | 不作为 Application 业务状态；S-10 Technical Design |

## 2. 关系与归属

| 主体 | 关系 | 客体 | 约束/含义 |
| --- | --- | --- | --- |
| User | 1 : 1 | Candidate | `candidate.user_id` 唯一 |
| User | 1 : 1 | HrProfile | `hr_profile.user_id` 唯一 |
| User | 1 : N | UserRole | 角色关联必须由服务端复核 |
| Candidate | 1 : N | Resume | Resume 只能归属于本人 Candidate |
| Candidate | 1 : N | CandidateDocument | 附加资料只能归属于本人 Candidate |
| Candidate | 1 : 1 | JobGoal | 当前版本每个 Candidate 只有一个当前目标；目标不绑定 Resume |
| Candidate | 1 : 0..1 | Resume | `current_resume_id` 表达当前简历；当前简历删除后置空，历史简历不自动回退 |
| Resume | 1 : 1 | CandidateProfile | 成功解析的 Resume 至多一个画像；画像另行表达匹配资格 |
| Candidate | 1 : N | AgentRunContext | 运行上下文只能归属于本人 Candidate；当前目标与运行上下文组合唯一 |
| JobGoal | 1 : N | AgentRunContext | 运行上下文保存启动时目标快照；当前版本同一 Candidate/JobGoal 不创建第二个运行 |
| Resume / CandidateProfile | 1 : N | AgentRunContext | 运行上下文绑定启动时有效的简历和其已校验画像 |
| Resume / CandidateDocument | N : 1 | StoredFileObject | 业务资源引用内部文件对象；不公开对象定位 |
| HrProfile | 1 : N | Job | Job 只能归属于创建它的 HrProfile |
| Job | 1 : 1 | StoredFileObject | 一份 Job 绑定一个 JD 文件；JD 输入不单独建实体 |
| Job | 1 : 0..1 | ParsedJobDescriptionSnapshot | 快照仅由 S-03 成功解析且五项核心字段有效后创建 |
| Job | 1 : 1 有效任务 | AsyncTaskRun | 新 Job 在上传事务内创建/复用 queued 解析任务；具体任务契约由 S-03 锁定 |
| AgentRunContext | 1 : N | Match | 一轮运行对每个可用 Job 最多保存一条 Match；`run_id + job_id` 唯一 |
| Match | 1 : 0..1 | Application | 仅 `matched` 结果创建 Application；创建后 Match 状态为 `application_created` |
| AgentRunContext | 1 : N | Application | 一轮运行对每个 Job 最多创建一条 Application；Application 必须关联同一轮 Match |
| Application | 1 : N | ProgressEvent | Application 创建和后续合法状态变化写入事件；事件不替代当前状态 |
| Application | 1 : 1 | Conversation | S-08 成功创建 Application 时幂等初始化的当前系统沟通会话；S10 只读取和写入当前 Conversation |
| Conversation | 1 : N | Message | 消息只属于一个 Conversation；HR/Agent 为发送主体 |
| Message | 1 : 0..1 | MessageAttachment | S10-02 一条 Agent 文本消息最多关联一个可下载附件；数据关系保留扩展空间但当前演示不交付多附件 |
| Conversation | 1 : N | AgentTurn | Agent Turn 记录执行幂等和状态，不改变 Application 状态 |

## 3. 身份与资源授权

| 资源 | 授权链 | 必须校验 |
| --- | --- | --- |
| Resume / CandidateDocument | `CurrentIdentity → Candidate → resource` | 当前 Candidate 归属 |
| Job | `CurrentIdentity → HrProfile → Job` | 当前 HR 归属 |
| Job 的 JD 文件 | `CurrentIdentity → HrProfile → Job → StoredFileObject` | Job 归属和文件关联 |
| S-03 解析任务 | `CurrentIdentity/任务上下文 → Job → StoredFileObject` | Job 存在、归属有效、文件可读；任务不得接收路径或正文 |

资源访问不得仅凭资源 ID 授权；`active_role` 只表示工作区上下文，不等同于资源权限。

## 4. 状态与合法迁移

| 对象 | 状态/迁移 | 状态拥有者 | 约束 |
| --- | --- | --- | --- |
| StoredFileObject | `writing → ready → deleting` | 文件对象/清理流程 | 只有 `ready` 对象可被业务资源读取 |
| Resume | `processing → succeeded / failed`；终态后可逻辑移除 | S-04 解析流程；S-11 删除 | `succeeded` 必须有已校验画像；画像另行判定 `matching_ready / matching_not_ready`；`failed` 只能记录受控 `failure_code`；相同内容上传复用既有资源；仅解析终态且 Agent 未启动时可移除 |
| CandidateDocument | `ready → success / failed`（业务投影）；`success → logically removed` | S-05 上传流程；S-11 删除 | `ready` 和 `failed` 为上传过程的瞬时业务结果，不写入 CandidateDocument；仅 `success` 资料形成持久化记录；逻辑移除后不参与新的资料检索，已创建附件保留有效期 |
| AsyncTaskRun | `queued → running → succeeded / failed` | Dispatcher/Worker 与任务流程 | `running` 受租约保护；终态不可被迟到回调覆盖 |
| Job | 创建后作为稳定岗位资源存在；逻辑移除后不再是当前可用岗位 | S-02 创建；S-11 删除 | 新 JD 创建新 Job；不覆盖、不建版本；删除资格受解析终态和匹配发起事实约束 |
| Job 的 JD 解析状态 | `queued / running / succeeded / failed` 的任务/资源状态 | S-03 | S-02 只创建/复用 queued 任务，不写解析终态；临时技术失败和输入不可用进入 `parse_failed`，核心字段缺失也进入 `parse_failed + matching_not_ready` 且不创建快照 |
| Job 删除资格 | 解析任务终态且未发起匹配 → 可删除；`queued/running` 或已发起匹配 → 不可删除 | S-11 执行，S-08 提供匹配发起事实 | 即使匹配失败或无结果，已发起匹配也不得删除；删除成功后不保留可用解析快照 |
| JobGoal | `active` 可由 S-06 创建/更新；`achieved` / `abandoned` 不可由 S-06 修改 | S-06 创建/更新；S-07/后续流程负责运行与达成 | 目标只保存用户输入，不绑定简历，不启动 Agent |
| AgentRunContext | `running → finished`；S-07 只创建 `running` | S-07 创建和幂等复用；后续流程结束运行 | 同一 Candidate/JobGoal 重复启动返回既有上下文；运行中或结束后不能开启新运行 |
| Match | `filtered_out`、`not_matched`、`matched`、`application_created` | S-08 | 同一 `run_id + job_id` 只保存一条；未形成 Application 的 Match 不进入 Candidate 进度页 |
| Application | `submitted →` 后续招聘阶段 | S-08 创建；S-09 推进 | 初始创建必须关联 `matched` Match；状态变化必须通过状态机和 ProgressEvent |
| ProgressEvent | `application_created` 及后续合法事件 | Application 状态拥有者 | 事件追加保存，不得伪造前状态或绕过状态机 |
| Conversation | 当前 Application 的会话容器；不新增独立业务状态 | S-08 初始化；S10 读取 | 只允许读取当前 Application 对应会话；一条 Application 只能有一个当前 Conversation |
| Message | `pending → sent / failed` | Conversation Message Service | 只有 `sent` 消息对 HR 可见 |
| MessageAttachment | `preparing → downloadable / failed → expired` | Attachment Service | `downloadable` 支持下载；创建后 7 天进入 `expired`；不支持在线预览；CandidateDocument 删除不影响有效期内的已发送附件 |
| AgentTurn | `accepted → processing → completed / waiting / failed` | Agent Workflow Service | Agent 编排状态不等于 Application 或 AgentRunContext 状态 |

S-09 的 HR Application 授权链为 `CurrentIdentity → HrProfile → Job → Application`，并复核 Application 关联的 Candidate 和 AgentRunContext。HR 视图只投影岗位名称、公司名称、候选人姓名和当前投递进度；内部标识不作为页面业务信息。

S-09 有效状态变化追加 `application_status_updated` 事件，操作者主体为 `hr`。相同状态重复提交不追加事件；终态 Application 不再产生状态事件。Offer 达标时，S-09 可在同一事务内结束 AgentRun 并将 JobGoal 标记为 `achieved`，但不锁定其它未终态 Application。

## 5. 解析结果与匹配资格

### 简历解析

| 结果 | 含义 | 后续影响 |
| --- | --- | --- |
| `parse_failed` | 文件不可读取、结构化结果无法校验或解析任务进入受控失败终态 | 不形成可用画像，不得创建可启动流程 |
| `parse_succeeded + matching_not_ready` | 画像已成功解析，但缺少姓名、简历内手机号/邮箱、教育经历，或工作经历与项目经历均缺失 | 不得启动 Agent；本次简历页不展示匹配资格详情 |
| `parse_succeeded + matching_ready` | 姓名、简历内手机号/邮箱、教育经历有效，且工作经历或项目经历至少一项有效 | 满足其他条件后可启动 Agent |

年龄属于可选画像信息，不影响匹配资格。`matching_ready` 是业务判定，不等同于 Resume 的解析终态，也不代表具体数据库字段。

CandidateProfile 的工作年限是由非实习工作年月确定性派生的 `unknown`、`x个月` 或 `x年`，不接受 LLM 估算值。

### 岗位 JD 解析

| 结果 | 含义 | 后续影响 |
| --- | --- | --- |
| `parse_failed` | 临时技术失败、输入不可用或核心字段缺失 | 不形成可供 S-08 使用的 `fields`；临时技术失败自动重试，输入不可用和核心字段缺失立即终止 |
| `parse_succeeded + matching_ready` | 五项核心字段均有效 | 可作为 S-08 的岗位 JD 输入 |

结构校验失败不属于当前受控演示版本的 JD 失败分支。

## 6. S-02 已确认规则

| 规则项 | 当前裁决 |
| --- | --- |
| 新 JD | 每份新 JD 文件创建一个新 Job |
| 覆盖/版本 | 不覆盖已有 Job；不建立 JD 版本链 |
| 顺序重复 | 同一 HrProfile 对相同文件内容，返回已有 Job 的幂等成功结果 |
| 跨 HR 相同内容 | 当前 Demo 不裁决业务复用规则 |
| 并发重复 | 当前 Demo 不纳入验收 |
| Job 展示字段 | Job 保存上传时的原始 `file_name`；岗位名称、公司、地点、薪资或摘要仍由 S-03 快照提供 |
| 批量上传 | 每个文件独立处理，允许部分成功 |
| 解析交接 | 新 Job 与 queued S-03 任务在同一事务内创建/复用；S-02 不直接调用 S-03、Dispatcher 或 Worker |

## 7. 变更规则

| 变化 | 处理 |
| --- | --- |
| 新增实体、关系或状态 | 先在对应 Slice Design 确认，再同步本文档 |
| Slice 契约与本文冲突 | 回退 Slice Design 并同步领域事实，不在代码中形成第二套定义 |
| Job 删除和下游引用 | 由 S-11/S-08 的 Slice Contract 补充；本表只保留已确认的删除资格规则 |
