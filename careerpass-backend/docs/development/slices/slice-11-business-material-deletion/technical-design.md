# S-11 业务资料删除 Technical Design

## 1. Facts and delivery linkage

- 业务事实源：`docs/business/business-baseline.md` 的 `BF-RULE-058` 至 `BF-RULE-063`、`BF-STATE-010`、`BF-STATE-012`、`BF-STATE-013`、`BF-SCOPE-007`、`BF-SCOPE-015`。
- Slice Spec：本目录 `slice-spec.md`。
- Contract：`docs/integration/slices/slice-11-business-material-deletion/integration-contract.md`，`IC-S11-BUSINESS-MATERIAL-DELETION@0.1`，已锁定。
- Scenario：`IS-S11-01`、`IS-S11-02`、`IS-S11-03`，均已标记为 `integration_delivered`。

## 2. API and handoff contract

在现有资源路由下分别增加删除命令：

- `DELETE /resumes/{resume_id}`；
- `DELETE /candidate_documents/{candidate_document_id}`；
- `DELETE /jobs/{job_id}`。

三个命令都要求 Bearer 身份、资源归属校验和统一响应。成功时逻辑删除立即提交；物理文件清理不阻塞响应，也不改变删除成功语义。

## 3. Data impact and transaction boundary

- `resumes.deleted_at` 和 `candidate_documents.deleted_at`：空值表示当前可用，非空表示逻辑删除。
- `candidates.current_resume_id`：指向当前简历；删除当前简历后置空，不自动回退历史简历。
- `jobs.deleted_at` 继续作为岗位逻辑删除标记。
- 新增 `resource_audit_events`，保存资源类型、资源 ID、操作者 ID、角色、事件类型和时间；`resource_type + resource_id + event_type` 唯一，保证重复删除不重复审计。
- 删除事务锁定资源和必要的当前身份行；逻辑状态、当前简历指针、岗位快照移除和审计记录同事务提交。
- Job 删除时移除当前可读的 `ParsedJobDescriptionSnapshot`；不删除 Match、Application、Conversation、Message 或 MessageAttachment。

## 4. Business state checks

| 资源 | 成功条件 | 拒绝条件 |
| --- | --- | --- |
| Resume | 当前简历；解析 `succeeded`/`failed`；无 AgentRunContext | 非当前简历；`processing`；存在 AgentRunContext |
| CandidateDocument | 已保存且未删除 | 仅资源不存在/归属不符；已删除按幂等成功 |
| Job | 归属当前 HR；最新 JD 任务 `succeeded`/`failed`；无 Match/Application | `queued`/`running`；已有 Match/Application；归属不符 |

`matching_ready` 与 `matching_not_ready` 只影响 Agent 启动，不影响 Resume 删除资格。

## 5. Implementation call chain

API → `BusinessResourceDeletionService` → `BusinessResourceDeletionRepository` → SQLAlchemy Session。Service 不直接访问 ORM；列表、上传、S-07 启动和 S10 资料检索的现有 Repository 同步加入逻辑删除过滤和当前简历语义。

上传规则同步调整：多个未删除 Resume 可以共存；新上传并实际创建的 Resume 更新 `current_resume_id`；已删除 Resume/CandidateDocument 不参与内容幂等复用。

S-07 启动改为读取 `current_resume_id`，不再使用“Resume 总数必须为 1”作为当前简历判定。

## 6. Error and security behavior

- 未登录：401；角色不符或资源不属于当前用户：403；资源不存在：404；状态不允许：409。
- 已删除资源：200 幂等成功，`deleted=false`，不新增审计。
- 日志只记录资源类型、资源 ID、操作者 ID、结果和错误分类；不记录正文、联系方式、文件对象键或异常原文。
- 新资料检索查询必须带 `CandidateDocument.deleted_at IS NULL`；MessageAttachment 下载只依赖附件自身、有效期和 HR 授权，不依赖来源资料仍未删除。

## 7. Readiness evidence

- 后端启动门禁：已完整读取 `careerpass-backend/docs/development/backend-troubleshooting.md`；本 Slice 未匹配既有故障案例。
- 后端统一预检已执行：`status=ready`、Docker CLI/Client/Compose/Engine 可用、context 为 `desktop-linux`、Compose 配置校验通过；Verify 阶段已重建 Compose 的 migrate、Backend、Worker 和 Dispatcher 服务。
- 依赖场景：S01、S04、S05、S07、S08、S10-02。
- 代码前置条件：迁移可升级、Repository 查询过滤完整、前端 Contract 映射和三份 Scenario 数据可执行。

## 8. Verification and rollback

- 单元：状态矩阵、归属、审计幂等、当前简历指针、已删除资料不参与重复上传。
- 集成：逻辑删除后列表/检索过滤、S10 既有附件下载、Job 快照移除和物理引用保护。
- 前端：三个正式页面的删除、错误、空状态和重复操作。
- 若 API、状态或当前简历语义变化，回退到 Slice Design，同步 Contract、Scenario、Mock 和前后端文档。

## 9. Close status

当前实现和跨端交付状态均为 `integration_delivered`。开发者已完成三类资源删除验收，S11 交付目标达成；后续仅保留常规回归维护。
