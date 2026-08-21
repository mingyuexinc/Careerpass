# S-11 业务资料删除 Slice Spec

## 1. Goal

授权用户可以删除当前可删除的简历、附加资料或岗位 JD；删除后资源不再出现在当前业务列表或新的业务检索中，既有业务历史保持可用。

## 2. Input

- 当前登录身份和角色；
- 资源 ID；
- 资源所属业务关系。

## 3. Output

- 删除成功或幂等成功结果；
- 当前资源列表更新后的可观察状态；
- 状态不允许、资源不存在或无权访问时的统一错误结果。

## 4. Preconditions

- 候选人或 HR 身份已由服务端验证；
- 资源属于当前身份；
- 资源状态满足本 Slice 的删除资格；
- 删除操作不改变已产生的 Agent、Application、Message 或 MessageAttachment 历史。

## 5. Business Rules

业务规则引用项目业务基线：`BF-RULE-058` 至 `BF-RULE-063`、`BF-STATE-010`、`BF-STATE-012`、`BF-STATE-013`、`BF-SCOPE-007`、`BF-SCOPE-015`。

本 Slice 不重复定义业务事实；接口和持久化方案由 Technical Design 与 Integration Contract 承接。

## 6. Scope / Non-goals

### Scope

- Resume、CandidateDocument、Job 的逻辑删除；
- 资源归属和状态校验；
- 删除审计和幂等；
- 当前简历切换、列表过滤和后续资料检索过滤；
- 已创建 MessageAttachment 的 7 天保留行为。

### Non-goals

- 物理删除数据库资源或文件对象；
- 回收站、恢复和删除原因；
- 修改 Agent、Application、Conversation、Message 或既有附件历史；
- 匹配与删除并发协调。

## 7. Technical Constraints

- 数据访问只能经过 Repository；
- 逻辑删除和审计记录在同一事务中完成；
- 物理对象只在没有有效引用时由既有清理流程处理；
- API 使用统一 `{code,msg,data}` 响应；
- 删除操作不输出或记录正文、联系方式、对象定位和原始异常；
- 当前简历由 Candidate 的可空当前指针表达，删除后不自动回退历史简历；新上传并形成的新简历成为当前简历。

## 8. Acceptance Criteria

- 简历：`succeeded`/`failed` 且 Agent 未启动可删除；`processing` 或 Agent 已启动不可删除；`matching_ready`/`matching_not_ready` 不改变删除资格；仅当前简历可删除。
- 附加资料：成功保存后在 Agent 全部生命周期均可删除；删除后不参与新检索；已有附件在 7 天内继续可下载。
- 岗位 JD：解析 `succeeded`/`failed` 且匹配未开始可删除；`queued`/`running` 或匹配已开始不可删除；删除后不再提供当前 S-03 快照。
- 同一资源重复删除返回幂等成功且只保留一条删除审计事件。
- 非归属用户不能通过资源 ID 删除资源。
- 正式前端的资源卡片、列表、空状态和错误提示与 Contract 一致。

### 8.1 Delivery Scenario

- `IS-S11-01`：候选人简历删除；
- `IS-S11-02`：候选人附加资料删除与 S10 附件保留；
- `IS-S11-03`：HR 岗位 JD 删除。
- Contract：`IC-S11-BUSINESS-MATERIAL-DELETION@0.1`，状态 `locked`。
- 开发者验证结论：三个场景的正式前端最小路径和状态矩阵均已通过，删除结果、列表过滤、权限、幂等和附件保留规则符合 Contract。
- Close 结论：自动化测试、前端 Mock/API/页面一致性、真实后端联调和开发者验收产物均已完成；S11 交付目标达成，状态为 `integration_delivered`。

## 9. Developer decisions required

无。
