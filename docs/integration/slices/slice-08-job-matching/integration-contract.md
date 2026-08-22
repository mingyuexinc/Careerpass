# Integration Contract：S-08 岗位匹配与投递

> Contract ID：`IC-S08-JOB-MATCHING@0.1`。状态：`locked`。
>
> 本契约覆盖 S-07 启动后同步执行 S-08、Match/Application 结果持久化和 Candidate 进度查询；不覆盖 S-09 HR 投递状态更新。

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| Slice | `S-08` |
| Scenario | [`IS-S08-01`](integration-scenario.md) |
| Producer | S-08 后端同步匹配与投递服务 |
| Consumer | Candidate 求职进度页 |
| 启动入口 | `POST /api/v1/agent_runs/current/start` |
| 结果查询 | `GET /api/v1/applications/current` |
| 响应格式 | `{code, msg, data}` |
| 执行方式 | S-07 事务提交后同步执行，岗位池最多 20 个 |

## 2. 业务边界

- 前端不提交匹配命令，不轮询匹配任务状态；
- Candidate 只使用关联 HR 中未删除、解析状态为 `succeeded` 且存在结构化快照的 JD；过滤后最多取 20 个；
- Match 独立持久化，Application 只由通过投递筛选的 Match 创建；
- 进度页只读取 Application，不读取未投递 Match；
- 没有任何有效 JD 时，S-07 返回 `409`，不创建运行；至少一个有效 JD 进入算法后全部未形成 Application 时，才返回 `finished/no_match`；
- 同一 `run_id + job_id` 只允许一条 Match 和一条 Application；
- 不处理真实外部投递、异步匹配和匹配失败业务分支。

## 3. 启动接口

### 3.1 Request

```http
POST /api/v1/agent_runs/current/start
Authorization: Bearer <access-token>
Content-Type: application/json
```

请求体为空对象 `{}`，不接受 Candidate、Resume、Job、算法版本或筛选参数。

### 3.2 Success response

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "run": {
      "id": "uuid",
      "status": "running",
      "started_at": "timestamp",
      "finished_at": null,
      "finish_reason": null
    }
  }
}
```

无投递结束时 `status` 为 `finished`、`finish_reason` 为 `no_match`。启动流程只返回 S-08 同步完成后的结果，不返回 Match 列表。

### 3.3 Idempotency

重复启动返回当前 Candidate 的既有运行上下文；S-08 通过 `run_id + job_id` 检查避免重复筛选和重复投递。

## 4. Application 查询接口

### 4.1 Request

```http
GET /api/v1/applications/current
Authorization: Bearer <access-token>
```

不接受资源 ID、Candidate ID 或 Job ID，由服务端从当前身份确定查询范围。

### 4.2 Success response

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "run": {
      "id": "uuid",
      "status": "finished",
      "finish_reason": "no_match"
    },
    "applications": [],
    "total": 0,
    "matching": {
      "active_job_count": 7,
      "eligible_job_count": 5,
      "pending_job_count": 1,
      "failed_job_count": 1,
      "evaluated_job_count": 5,
      "filtered_out_job_count": 2,
      "matched_job_count": 0
    }
  }
}
```

有投递时，每条 Application 至少包含：

| 字段 | 说明 |
| --- | --- |
| `id` | Application 标识 |
| `job_id` | 岗位标识 |
| `status` | 初始为 `submitted` |
| `job_title` | 岗位名称 |
| `company_name` | 安全展示字段，可为空 |
| `location` | 工作地点 |
| `salary` | 薪资展示字段 |
| `match_score` | `0–100` 推荐匹配得分 |
| `recommendation_reason` | 规则模板生成的推荐理由 |
| `applied_at` | 系统内投递创建时间 |

### 4.3 空结果语义

前端根据 `matching` 摘要区分：有 `pending_job_count` 或 `failed_job_count` 且无有效岗位时展示“岗位尚未准备完成”；存在有效岗位但部分未参与时展示未参与数量；至少一个岗位已进入算法且 Application 为 0 时展示“本轮暂未产生匹配结果”。

## 5. 错误与安全

| 情况 | 响应语义 |
| --- | --- |
| 未登录 | `401`，统一认证失败响应 |
| 当前身份不是 Candidate | `403`，不得读取 Candidate 数据 |
| 不属于当前 Candidate 的资源 | 不返回资源存在性细节 |
| 请求字段不合法 | `400`，统一校验错误 |

当前 Demo 不验收匹配失败和 Application 创建失败的业务页面；实现仍不得返回原始异常、简历原文、JD 原文、文件路径、Token 或模型响应。

## 6. Schema 与实现约束

- Pydantic Schema 必须拒绝未定义字段；
- Repository 负责归属过滤和唯一性查询；
- Service 负责业务编排和状态迁移；
- API 只负责身份依赖、参数接收和统一响应；
- Match 不提供 Candidate 前端查询接口；
- S-09 后续通过状态机推进 Application，不由前端直接修改状态。
