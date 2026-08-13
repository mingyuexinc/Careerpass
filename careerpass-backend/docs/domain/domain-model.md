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
| Resume | 持久化实体 | Candidate | 保存正式简历和解析状态 | `implemented` | 当前代码与迁移 |
| CandidateProfile | 持久化实体 | Resume | 保存成功解析后的结构化候选人画像 | `implemented` | `resume_id` 一对一 |
| CandidateDocument | 持久化实体 | Candidate | 保存附加求职资料，不进入解析状态机 | `implemented` | 当前代码与迁移 |
| AsyncTaskRun | 持久化实体 | 关联业务资源 | 保存异步任务权威状态、租约、幂等和脱敏失败分类 | `implemented` | 当前已支持简历解析；岗位任务由后续 Slice 扩展 |
| Job | 持久化实体 | HrProfile | 表示一份独立岗位，关联一个 JD 文件并作为 S-03 输入锚点 | `slice-confirmed` | S-02 已确认，代码/迁移待实现 |
| ParsedJobDescriptionSnapshot | 持久化实体 | Job | 保存 S-03 解析并校验后的岗位结构化事实和展示字段 | `deferred to S-03` | 不由 S-02 创建 |
| JobGoal / Match / Application / Conversation / Message / ProgressEvent | 持久化实体 | 待对应业务主体确认 | 求职目标、匹配、投递、沟通和事件 | `not confirmed` | 不提前写入当前事实源 |

## 2. 关系与归属

| 主体 | 关系 | 客体 | 约束/含义 |
| --- | --- | --- | --- |
| User | 1 : 1 | Candidate | `candidate.user_id` 唯一 |
| User | 1 : 1 | HrProfile | `hr_profile.user_id` 唯一 |
| User | 1 : N | UserRole | 角色关联必须由服务端复核 |
| Candidate | 1 : N | Resume | Resume 只能归属于本人 Candidate |
| Candidate | 1 : N | CandidateDocument | 附加资料只能归属于本人 Candidate |
| Resume | 1 : 1 | CandidateProfile | 成功解析的 Resume 至多一个画像 |
| Resume / CandidateDocument | N : 1 | StoredFileObject | 业务资源引用内部文件对象；不公开对象定位 |
| HrProfile | 1 : N | Job | Job 只能归属于创建它的 HrProfile |
| Job | 1 : 1 | StoredFileObject | 一份 Job 绑定一个 JD 文件；JD 输入不单独建实体 |
| Job | 1 : 0..1 | ParsedJobDescriptionSnapshot | 快照由 S-03 成功解析后创建 |
| Job | 1 : 1 有效任务 | AsyncTaskRun | 新 Job 在上传事务内创建/复用 queued 解析任务；具体任务契约由 S-03 锁定 |

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
| Resume | `processing → succeeded / failed` | S-03 解析流程 | `succeeded` 必须有已校验画像；`failed` 只能记录受控 `failure_code` |
| AsyncTaskRun | `queued → running → succeeded / failed` | Dispatcher/Worker 与任务流程 | `running` 受租约保护；终态不可被迟到回调覆盖 |
| Job | 创建后作为稳定岗位资源存在 | S-02 创建；S-11 删除 | 新 JD 创建新 Job；不覆盖、不建版本 |
| Job 的 JD 解析状态 | `queued / running / succeeded / failed` 的任务/资源状态 | S-03 | S-02 只创建/复用 queued 任务，不写解析终态 |
| Job 删除资格 | `未发起匹配 → 可删除`；`已发起匹配 → 不可删除` | S-11 执行，S-08 提供匹配发起事实 | 即使匹配失败或无结果，已发起匹配也不得删除 |

## 5. S-02 已确认规则

| 规则项 | 当前裁决 |
| --- | --- |
| 新 JD | 每份新 JD 文件创建一个新 Job |
| 覆盖/版本 | 不覆盖已有 Job；不建立 JD 版本链 |
| 顺序重复 | 同一 HrProfile 对相同文件内容，返回已有 Job 的幂等成功结果 |
| 跨 HR 相同内容 | 当前 Demo 不裁决业务复用规则 |
| 并发重复 | 当前 Demo 不纳入验收 |
| Job 展示字段 | Job 不保存岗位名称、公司、地点、薪资或摘要；由 S-03 快照提供 |
| 批量上传 | 每个文件独立处理，允许部分成功 |
| 解析交接 | 新 Job 与 queued S-03 任务在同一事务内创建/复用；S-02 不直接调用 S-03、Dispatcher 或 Worker |

## 6. 变更规则

| 变化 | 处理 |
| --- | --- |
| 新增实体、关系或状态 | 先在对应 Slice Design 确认，再同步本文档 |
| Slice 契约与本文冲突 | 回退 Slice Design 并同步领域事实，不在代码中形成第二套定义 |
| Job 删除和下游引用 | 由 S-11/S-08 的 Slice Contract 补充；本表只保留已确认的删除资格规则 |
