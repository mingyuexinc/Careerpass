# Integration Contract：S11 业务资料删除

> Contract ID：`IC-S11-BUSINESS-MATERIAL-DELETION@0.1`
> 关联 Slice：S11 业务资料删除
> 关联 Scenario：`IS-S11-01`、`IS-S11-02`、`IS-S11-03`
> Producer：S11 后端服务
> Consumer：求职者资料页、HR 岗位 JD 页、S10 资料检索
> 状态：`locked`

## 1. 用户场景与边界

- 候选人删除当前简历或已保存附加资料；HR 删除自己上传的岗位 JD。
- 删除成功后资源从当前列表和新的业务检索中消失。
- 既有 Agent 运行、投递、消息和已经创建的附件不被改写。
- 三类资源均为逻辑删除；不提供恢复、回收站或删除原因。

## 2. 请求契约

| 资源 | 方法与路径 | 身份与归属 |
| --- | --- | --- |
| Resume | `DELETE /api/v1/resumes/{resume_id}` | 当前 Candidate，且只能删除当前简历 |
| CandidateDocument | `DELETE /api/v1/candidate_documents/{candidate_document_id}` | 当前 Candidate |
| Job | `DELETE /api/v1/jobs/{job_id}` | 当前 HR，且 Job 属于当前 HrProfile |

请求无 body、无删除原因、无额外幂等键。资源 ID 必须是 UUID。

## 3. 响应契约

所有响应遵循 `{code,msg,data}`。

成功和幂等成功：HTTP 200，`code=200`，数据为：

```json
{
  "resource_type": "resume",
  "resource_id": "00000000-0000-0000-0000-000000000000",
  "deleted": true
}
```

重复删除返回相同结构但 `deleted=false`，不重复写审计。

| 场景 | HTTP / code | 页面结果 |
| --- | --- | --- |
| 删除成功 | 200 / 200 | 卡片从列表移除并刷新空状态/当前状态 |
| 重复删除 | 200 / 200 | 保持列表状态，不产生重复提示或审计 |
| 未登录 | 401 / 401 | 登录失效 |
| 角色或归属不符 | 403 / 403 | 资源不可用，不泄露详情 |
| 资源不存在 | 404 / 404 | 资源不存在或已不可用 |
| 状态不允许 | 409 / 409 | 展示受控原因，保持原列表 |

## 4. 状态与后续使用

| 资源 | 可删除 | 不可删除 | 删除后 |
| --- | --- | --- | --- |
| Resume | 解析 `succeeded`/`failed` 且 Agent 未启动的当前简历 | `processing`、非当前简历、Agent 运行中/已结束 | 当前简历为空；历史简历不自动回退；新上传形成的新简历成为当前 |
| CandidateDocument | 成功保存后的任意 Agent 生命周期 | 无额外 Agent 状态限制 | 新检索不可命中；既有 MessageAttachment 7 天内可下载 |
| Job | JD 解析 `succeeded`/`failed` 且无 Match/Application | `queued`/`running` 或匹配已开始 | 从 HR 当前列表移除，不再提供 S-03 当前快照 |

## 5. 安全、幂等与兼容

- 服务端始终按当前用户和资源归属授权，不能仅凭资源 ID。
- 删除状态和审计事件同事务提交。
- 物理文件只由已有对象清理流程在无有效引用时处理。
- 审计仅保存关联 ID、资源类型、资源 ID、操作者、事件类型和时间；不保存正文、联系方式、对象定位、删除原因或原始异常。
- Contract 变化必须回退 Slice Design，并同步前端 Mock、后端 Schema、Scenario 和文档。

## 6. 锁定记录

| 日期 | 变化 | 影响 | 回退 Gate | 结论 |
| --- | --- | --- | --- | --- |
| 2026-08-21 | 首次锁定 S11 删除契约 | 前端、后端、S10-02 | Slice Design | `locked` |
