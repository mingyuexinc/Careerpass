# S-09 投递进度更新技术设计

> 本文档只记录当前 Slice 的技术落地事实和证据。
>
> 业务目标、输入、输出、前置条件、业务规则、范围和验收标准以同目录的 `slice-spec.md` 为准；跨端字段、状态和错误语义以 Integration Contract 为准。
>
> 状态：`implemented` / `integration_delivered`。S-09 已完成后端实现、前端接入和自动化联调验证。

## 1. 文档职责与事实源

| 内容 | 事实源 |
| --- | --- |
| Slice 目标、范围和验收 | [`slice-spec.md`](./slice-spec.md) |
| 跨前后端业务事实 | [`business-baseline.md`](../../../../../docs/business/business-baseline.md) |
| API、字段和错误语义 | [`integration-contract.md`](../../../../../docs/integration/slices/slice-09-application-progress-update/integration-contract.md) |
| 场景演示、整改和关闭证据 | [`integration-scenario.md`](../../../../../docs/integration/slices/slice-09-application-progress-update/integration-scenario.md) |
| 领域实体和状态拥有者 | [`domain-model.md`](../../../domain/domain-model.md) |
| 数据库事实 | [`database-design.md`](../../../data/database-design.md) |
| 跨 Slice 规则 | [`business-rules.md`](../../../product/business-rules.md) |

### 1.1 交付关联

| 项目 | 约定 |
| --- | --- |
| Integration Scenario | [`IS-S09-01`](../../../../../docs/integration/slices/slice-09-application-progress-update/integration-scenario.md) |
| Integration Contract | [`IC-S09-APPLICATION-PROGRESS@0.1`](../../../../../docs/integration/slices/slice-09-application-progress-update/integration-contract.md) |
| 后端状态 | `backend_ready`；代码、隔离 PostgreSQL 和测试已验证 |
| 跨端交付状态 | `integration_delivered` |
| 演示目标 | HR 登录后恢复岗位和投递，查看四项字段并推进投递状态，求职者刷新确认变化，验证错误边界和 Offer 达标联动。 |

## 2. API、异步任务与交接契约

### 2.1 HR 查询当前投递

```text
GET /api/v1/applications/hr/current
```

服务端要求当前活动角色为 HR，并以 `CurrentIdentity → HrProfile → Job → Application` 查询当前 HR 所有未删除 Job 下当前首轮 AgentRun 的 Application。

`data` 至少包含：

```json
{
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
```

页面只展示 `job_title`、`company_name`、`candidate_name` 和 `status`；`id`、`job_id` 仅供前端更新和分组使用。

四项页面业务信息与 Contract 一致，分别为岗位名称、公司名称、候选人姓名和当前投递进度。

### 2.2 HR 恢复当前岗位

```text
GET /api/v1/jobs/hr/current
```

该接口是 HR 工作区恢复所需的支持查询。服务端仅按 `CurrentIdentity.hr_profile_id` 返回当前 HR 未删除的 Job，并返回上传时持久化的 `file_name`，同时从已校验的 `ParsedJobDescriptionSnapshot` 投影岗位名称、公司名称；快照缺失或解析任务尚未完成时返回安全空值和 `parse_status`，不返回 JD 原文、文件路径或对象键。

`data` 结构为 `jobs` 与 `total`。正式前端进入 HR 工作区时同时刷新岗位和投递；岗位文件名属于 Job 上传元数据，不使用解析后的岗位名称替代。

### 2.3 更新单条投递状态

```text
PATCH /api/v1/applications/{application_id}/status
```

请求体：

```json
{
  "status": "screening"
}
```

响应返回更新后的 HR 投影，不额外暴露联系方式、简历原文、匹配信息、沟通内容或内部文件定位。所有响应使用 `{code, msg, data}`。

### 2.4 异步任务契约

本 Slice 不产生异步任务。状态更新、事件写入、Offer 统计及 AgentRun/JobGoal 联动均在同步请求的同一事务中完成。

### 2.5 交接契约

S-09 不新增跨 Slice Handoff Contract。求职者侧继续消费既有 S-08 投递查询能力；S-09 状态提交成功后，求职者通过刷新或重新进入页面读取最新状态，不引入实时推送。

## 3. 领域实体与数据影响

### 3.1 实体使用

| 实体 | 本 Slice 用途 | 读写变化 | 归属/授权 | 全局事实源 |
| --- | --- | --- | --- | --- |
| `Application` | 查询当前投递、更新当前状态 | 查询 / 修改 | 通过当前 HR → Job → Application 校验 | [`domain-model.md`](../../../domain/domain-model.md) |
| `ProgressEvent` | 记录有效状态迁移 | 创建 | 与 Application、Job、Candidate 关系一致 | [`domain-model.md`](../../../domain/domain-model.md) |
| `Job` | 确认未删除岗位及 HR 归属，提供上传文件名 | 查询 | 当前 HR 所有 | [`domain-model.md`](../../../domain/domain-model.md) |
| `CandidateProfile` | 提供已校验候选人姓名 | 查询 | 与 Application 关联的 Candidate | [`domain-model.md`](../../../domain/domain-model.md) |
| `AgentRunContext` | 限定当前首轮投递并统计 Offer | 查询 / 达标时修改关联 AgentRun | 与 Application 和 JobGoal 关系一致 | [`domain-model.md`](../../../domain/domain-model.md) |
| `JobGoal` | Offer 达标时转为 `achieved` | 达标时修改 | 当前 Candidate 的当前目标 | [`domain-model.md`](../../../domain/domain-model.md) |

### 3.2 数据库影响

- 不新增业务实体或业务表；为支持岗位卡片恢复新增 `jobs.file_name` 上传元数据字段，并由 `20260819_0014` Alembic 迁移落地；
- 复用 `applications.updated_at` 保存更新时间，复用 `progress_events` 保存状态变更审计；
- 状态更新、ProgressEvent、Offer 统计、AgentRun 和 JobGoal 达标联动为同一事务；
- 数据库事实源：[`database-design.md`](../../../data/database-design.md)。

### 3.3 状态与业务规则同步

- 状态集合和合法迁移复用业务基线 `BF-STATE-005` 至 `BF-STATE-008`；
- HR 查询和更新规则复用 `BF-RULE-039` 至 `BF-RULE-044`；
- 本 Slice 已同步更新领域模型、数据库设计和 `business-rules.md`，不新增全局状态。

## 4. 技术实现方案

### 4.1 分层与调用链

```text
HTTP API
  → 身份与请求校验
  → Application Service / 状态迁移与 Offer 联动
  → Repository / 归属查询、行锁、持久化
  → 安全 HR 投影与统一响应
```

### 4.2 Repository 与 Service 边界

Repository 负责：

- 查询当前 HR 所属 Job、当前首轮 AgentRun 和 Application；
- 在当前单 Candidate 受控演示中，“当前首轮”取全局最新的 `AgentRunContext`；历史 Candidate 的旧 AgentRun 不进入 HR 当前投递视图；
- 以 `SELECT ... FOR UPDATE` 锁定待更新 Application；
- 校验 Job 未删除、Job 属于当前 HR、Application 与 Job/Candidate/AgentRun 关系一致；
- 写入 Application 状态、`updated_at` 和 ProgressEvent；
- 统计当前 AgentRun 的 Offer 数量并更新 AgentRun/JobGoal。

Service 负责：

- 校验 HR 身份；
- 调用状态迁移规则；
- 组织单事务中的状态更新、事件追加和 Offer 联动；
- 将 Repository 结果映射为安全 HR 投影。

Service、Agent 或 Workflow 不直接访问 ORM Session 或编写 SQL。

### 4.3 局部实现决策

| 决策 | 选择 | 简短理由 |
| --- | --- | --- |
| HR 查询结果形态 | 扁平 Application 列表，由前端按岗位分组 | 复用现有投递查询能力，减少后端聚合边界 |
| Offer 达标一致性 | 与状态更新同一事务同步完成 | 避免 Application、ProgressEvent、AgentRun 和 JobGoal 暂时不一致 |
| 求职者刷新语义 | 复用既有查询，不新增推送 | 满足演示闭环且不扩大 S-09 范围 |
| HR 工作区恢复 | 独立 `HrJob` 投影与 Application 投影分别刷新 | 避免页面局部上传状态遮蔽数据库中的岗位事实，并隔离角色数据 |

## 5. 状态、事件和事务

- 状态顺序和终态规则复用业务基线，不允许接口自行定义第二套状态机；
- 有效状态变化写入 `event_type=application_status_updated`、准确的 `from_status`、`to_status`、`actor=hr` 和服务端时间；
- 相同状态重复请求返回幂等成功，不新增事件；
- 非法回退、终态修改、无效状态和无权 Application 返回业务失败，原状态不变；
- Application 更新、ProgressEvent 写入、Offer 统计、AgentRun 结束和 JobGoal 达成在同一事务中提交；
- AgentRun 结束不锁定其它未终态 Application；
- 不新增异步任务，不产生外部投递或消息副作用。

## 6. 外部依赖、失败处理与安全边界

### 6.1 依赖与证据

| 依赖 | 用途 | 真实证据 | 状态 |
| --- | --- | --- | --- |
| S-01 认证与当前身份 | 识别 HR 工作区 | 复用 `CurrentIdentity.hr_profile_id`，API 测试覆盖 HR/非 HR | 通过 |
| S-08 Application 与 ProgressEvent | 提供当前首轮投递 | PostgreSQL 集成测试验证当前首轮、归属过滤和事件追加 | 通过 |
| PostgreSQL 事务 | 保证状态、事件和 Offer 联动一致 | 隔离 Compose PostgreSQL、迁移和 S-09 集成测试通过 | 通过 |

后端统一预检 `scripts/backend-readiness.ps1` 返回 `status=ready`；隔离环境 Alembic `upgrade head` 成功，`20260819_0014` 已应用。

### 6.2 失败处理

- 未登录：返回 401 统一认证失败；
- 非 HR 身份：返回 403；
- 不存在或不属于当前 HR 的 Application：返回 404/403 的统一资源不可用语义，不泄露归属信息；
- 非法状态迁移：返回 409，原状态保持不变；
- 请求体状态无效：返回 400 校验错误；
- 事务失败：整体回滚，不产生部分状态、事件或联动更新；
- 同状态重复请求：幂等成功，不新增事件。

### 6.3 敏感信息

HR 响应不得包含联系方式、简历原文、匹配分数、推荐理由、沟通全文、模型原始响应或内部文件定位。日志只记录 Application、Job、AgentRun 的关联 ID、前后状态、阶段和结果分类，不记录敏感原值。

## 7. 不变式

- 一次更新最多改变一条 Application；
- 每次有效状态变化最多追加一条 ProgressEvent；
- ProgressEvent 的前状态必须等于更新前 Application 状态；
- `offer` 和 `terminated` 之后不能产生新的状态事件；
- HR 查询永远不会返回其它 HR 的 Job 或 Application；
- S-08 的 Candidate 查询接口和字段保持不变。
- HR 重新登录后可恢复本人岗位和投递，HR 与 Candidate 切换不会复用旧工作区数据。

## 8. 验证结果与关闭结论

### 8.1 Readiness Check

已通过。Docker CLI、Engine、Compose、PostgreSQL、Redis 和 Compose 配置均通过统一预检；现有模型关系、事务边界、错误映射和隔离测试入口均已核对。

### 8.2 验证证据

| 验证类型 | 覆盖内容 | 结果 | 证据 |
| --- | --- | --- | --- |
| 单元验证 | 状态迁移、幂等、终态、Offer 达标规则 | 通过 | `tests/unit/test_s09_application_progress.py`：8 passed |
| API / 集成验证 | 查询、更新、权限、错误和事务一致性 | 通过 | `tests/integration/test_s09_application_progress.py`：1 passed；前端 API 测试通过 |
| 前后端联调 | HR 岗位文件名恢复、四字段投递页面、状态更新和求职者读取最新状态 | 通过 | `IS-S09-01`；开发者完整流程演示通过；前端 19 个测试文件/63 个测试，构建通过 |
| 外部能力验证 | 异步或外部投递依赖 | 不适用 | 本 Slice 不产生 |

### 8.3 关闭结论

- `slice-spec.md` 与最终实现一致：是；
- 本文档与代码、迁移和测试一致：是；
- 全局领域、数据和业务事实已同步：是；
- Integration Contract 与前端 Mock、真实 API 一致：是；
- Integration Scenario 演示步骤通过：是；跨角色岗位恢复自动化、真实 PostgreSQL 归属链和容器健康检查通过；
- 未决开发者裁决：无；
- 最终结论：`integration_delivered`；后端与前端实现完成，岗位文件名恢复问题已整改并完成联调回归，S-09 交付目标达成。
