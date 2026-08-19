# Integration Contract：S-09 HR 投递进度管理

> Contract ID：`IC-S09-APPLICATION-PROGRESS@0.1`
> 关联 Slice：S-09 投递进度更新
> 关联 Scenario：`IS-S09-01`
> 状态：`locked`

## 1. 用户场景与边界

- 角色：已登录 HR；
- 查询范围：当前 HR 所有未删除岗位下的当前首轮 Application；当前受控单 Candidate 演示中的“当前首轮”取全局最新 `AgentRunContext`，不包含历史 Candidate 的旧运行；
- 页面展示：岗位名称、公司名称、候选人姓名、当前投递进度；
- 更新范围：当前岗位下当前候选人的单条 Application；
- 不包含：联系方式、简历原文、匹配分数、推荐理由、沟通全文、其它候选人资料、多轮投递和实时推送。

## 2. 请求契约

### 查询

```text
GET /api/v1/applications/hr/current
Authorization: Bearer <access_token>
```

HR 工作区恢复还调用：

```text
GET /api/v1/jobs/hr/current
Authorization: Bearer <access_token>
```

该支持查询只返回当前 HR 未删除岗位的 `id`、`file_name`、`job_title`、`company_name`、`created_at` 和 `parse_status`。`file_name` 是上传时保存的原始文件名，用于岗位 JD 上传卡片展示；它与投递查询独立，不能替代 Application 权限校验，也不返回 JD 原文、文件路径或对象键。

### 更新

```text
PATCH /api/v1/applications/{application_id}/status
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "status": "screening"
}
```

服务端复核 HR 身份、Job 归属、Application 关联的 Candidate/Job/AgentRun 和当前首轮范围。请求不接受 Candidate ID、Job ID 或权限范围作为客户端授权依据。

## 3. 响应契约

所有响应遵循 `{code, msg, data}`。

查询成功：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "applications": [
      {
        "id": "uuid",
        "job_id": "uuid",
        "job_title": "AI 应用开发工程师",
        "company_name": "示例公司",
        "candidate_name": "候选人姓名",
        "status": "submitted"
      }
    ],
    "total": 1
  }
}
```

更新成功返回相同的安全投影。内部 ID 只用于请求和前端分组，不作为页面业务信息展示。

## 4. 状态与错误

- 合法状态：`submitted`、`screening`、`written_test`、`interview_1`、`interview_2`、`interview_3`、`hr_interview`、`offer`、`terminated`；
- 非终态可向后跳转或进入 `terminated`；不允许回退；
- `offer`、`terminated` 为终态；终态修改返回 409；
- 相同状态重复提交返回成功，不新增事件；
- 有效更新追加 `application_status_updated` ProgressEvent，操作者为 `hr`；
- 进入 `offer` 后达到目标时，服务端同步结束 AgentRun 并将 JobGoal 标记为 `achieved`；其它未终态 Application 仍可更新；
- 未登录返回 401，非 HR 返回 403，资源不可用返回 404/403，非法迁移返回 409，请求状态无效返回 400；
- 更新失败时前端保留原状态并展示可理解的失败反馈。

## 5. 前端映射

| 后端 Schema / Contract 字段 | 前端 Mock 字段 | 正式页面用途 | 可见性 |
| --- | --- | --- | --- |
| `file_name`（HR Job 查询） | `fileName` | 岗位 JD 上传卡片文件名 | 展示 |
| `job_title` | `jobTitle` | 投递岗位名称 | 展示 |
| `company_name` | `companyName` | 投递公司名称 | 展示 |
| `candidate_name` | `candidateName` | 候选人姓名 | 展示 |
| `status` | `status` | 当前投递进度，并按统一状态映射显示文案 | 展示 |
| `id`、`job_id` | `id`、`jobId` | 更新请求和按岗位分组 | 内部使用，不展示 |

Mock 不保留联系方式、简历原文、匹配分数、推荐理由、沟通全文或其它候选人资料作为 HR 视图字段；求职者侧既有数据不因本 Contract 删除。

错误与页面表现：

- 401：清理失效工作区并返回登录入口；
- 403：展示无权访问提示，不展示资源详情；
- 404：展示记录不可用或空状态，不泄露资源归属；
- 409：保留当前状态并展示状态不可回退或终态不可修改的失败反馈；
- 400：展示状态输入校验失败，不提交状态变化。

Candidate 侧继续使用 S-08 的 `GET /api/v1/applications/current`，其匹配分数和推荐理由契约不因本 Contract 改变。

HR 退出后重新登录或切换角色时，前端清理旧工作区投影，并按新身份重新读取上述两个查询；不复用上一身份的岗位、投递或 Mock 会话数据。沟通页仍属于 S-10，本 Contract 不定义 Conversation/Message API。

## 6. 兼容与锁定记录

- 新增字段、状态或改变状态语义必须升 Major 版本并回退 Slice Design；
- Contract 变更必须同步更新 S-09 Slice Spec、Technical Design、前端 Mock 和 Integration Scenario；
- 本 Contract 不定义实时推送，求职者通过刷新或重新进入页面读取最新状态。
