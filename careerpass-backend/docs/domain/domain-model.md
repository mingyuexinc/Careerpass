# 后端领域模型

> 本文档只记录当前代码、迁移或具体 Slice 已确认的领域事实。状态属于领域模型，不单独维护状态文档。

## 1. 当前实体

| 实体 | 所有者与职责 |
| --- | --- |
| User | 持有用户名和密码哈希的认证账户 |
| Candidate | 与 User 一对一关联的求职者身份 |
| HrProfile | 与 User 一对一关联的 HR 业务身份 |
| UserRole | User 与可用业务身份之间的角色关联；用于校验登录工作区 |
| StoredFileObject | 内部去重文件对象，不直接归属于公开 API |
| Resume | Candidate 所有的正式简历，持有解析状态 |
| CandidateProfile | 从一份成功解析的 Resume 得到的一对一结构化画像 |
| CandidateDocument | Candidate 所有的附加资料，不进入解析状态机 |
| AsyncTaskRun | 简历解析异步工作的持久化权威状态 |

Job、JobGoal、Match、Application、Conversation、Message 和 ProgressEvent 当前未被代码或迁移确认，不属于本文档事实。

## 2. 认证上下文

`CurrentIdentity` 是认证依赖传递给业务代码的不可变运行时投影，不是独立持久化实体。它由服务端根据已验证的 `User`、`UserRole`、`Candidate` 和 `HrProfile` 关系组装，包含：

- `user_id`、`username` 和可选的展示名称；
- 用户拥有的 `roles`；
- 本次请求采用的 `active_role`；
- 与当前用户关联的可选 `candidate_id` 和 `hr_profile_id`。

`active_role` 只表示本次登录或请求使用的业务身份上下文，不等同于具体业务资源的访问权限。具体资源仍必须由对应业务切片按资源归属规则校验。

## 3. 关系与归属

- User 与 Candidate 一对一；Candidate.user_id 唯一且不可脱离 User 独立解析身份。
- User 与 HrProfile 一对一；HrProfile.user_id 唯一且不可脱离 User 独立解析身份。
- User 与 UserRole 一对多；UserRole 记录该 User 可使用的 `candidate` 或 `hr` 角色。
- 登录请求提供的 `active_role` 必须存在于该 User 的 UserRole 关联中，并且对应的 Candidate 或 HrProfile 身份关系必须能够由服务端复核。
- Resume、CandidateDocument 通过 candidate_id 归属于 Candidate。
- CandidateProfile 通过唯一 resume_id 归属于 Resume。
- Resume 和 CandidateDocument 通过 stored_file_object_id 引用内部文件对象。
- AsyncTaskRun 以 resource_type、resource_id 绑定当前支持的 Resume 解析资源。

资源读取和修改必须从当前身份校验以上归属链，不能仅依赖资源 ID。

## 4. 当前状态

### StoredFileObject

writing → ready → deleting

- 只有 ready 对象可以被业务资源读取。
- deleting 表示清理过程，不得恢复为公开可读。

### Resume

processing → succeeded 或 processing → failed

- succeeded 必须存在通过校验的 CandidateProfile。
- failed 必须记录受控 failure_code，不记录供应商原始错误。
- 终态不得由迟到 Worker 回写。

### AsyncTaskRun

queued → running → succeeded 或 queued/running → failed

- queued 是待投递或可重新投递状态。
- running 必须由有效 execution_token 和租约保护。
- succeeded、failed 为终态；旧租约和重复回调不得改变终态。

## 5. 增量规则

新实体、状态和合法迁移只在实际使用它们的 Slice Design 中确认。Slice 契约与本文冲突时，必须先回退并同步领域事实，不得在实现中形成第二套状态定义。
