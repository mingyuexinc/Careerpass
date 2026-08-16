# Slice：S-05 求职者资料上传

> 当前阶段：Close

> 当前状态：前后端代码、Contract、自动化验证和真实前端联调已完成；`IS-S05-01` 已标记为 `integration_delivered`。

## 1. 目标

已登录求职者可以一次选择一份或多份附加求职资料。系统逐文件校验并保存合法资料，前端显示 `ready`；成功资料加入当前求职者的资料列表，失败文件通过一次性错误 Toast 提示且不持久化。

交付场景：[`IS-S05-01`](../../../../../docs/integration/slices/slice-05-candidate-document-upload/integration-scenario.md)。

## 2. 输入与输出

| 项目 | 约束 |
| --- | --- |
| 输入身份 | 已登录且服务端确认的 Candidate |
| 上传粒度 | 一次请求可以提交一份或多份附加资料；每个文件独立处理 |
| 文件范围 | PDF、Markdown、JPG、PNG；单文件不超过 10 MB |
| 成功结果 | 文件形成 Candidate-owned 资料资源，状态为 `success`，并可在资料列表中展示 |
| 重复结果 | 同一 Candidate 的相同内容返回既有资料，作为幂等成功，不创建重复资源 |
| 失败结果 | 不支持格式、超过大小限制、对象存储失败或事务失败形成逐文件 `failed` 结果，不创建 CandidateDocument |
| 前端结果 | 选择后显示 `ready`；成功资料显示 `success` 并进入列表；失败文件不进入持久页面状态，批次完成后通过一次性 error Snackbar/Toast 提示，不提供重试入口 |

## 3. 前置条件

- S-01 已提供有效 `CurrentIdentity`，且当前工作区为求职者角色。
- 当前身份可以解析到唯一 Candidate。
- PostgreSQL、受控对象存储和 Candidate 资料 Repository 可用。

## 4. 业务规则

本 Slice 使用 `BF-ROLE-001`、`BF-OBJECT-002`、`BF-OBJECT-011`、`BF-FLOW-002`、`BF-FLOW-014`、`BF-FLOW-015`、`BF-RULE-003`、`BF-RULE-004`、`BF-RULE-010`、`BF-RULE-020`、`BF-RULE-021`、`BF-RULE-022`、`BF-RULE-023`、`BF-STATE-015` 和 `BF-SCOPE-017`。

- 同一批次逐文件处理；单文件失败不回滚同批次成功文件。
- 重复判断使用当前 Candidate 和文件内容摘要；命中既有资料时返回幂等成功，不创建第二条业务记录。
- `ready` 是前端上传过程状态；只有对象存储和数据库提交成功后才形成 `success` 资料资源。
- 失败文件不进入正式资料列表或持久页面状态；批次完成后通过一次性错误 Toast 提示，不提供重试入口。
- 资料默认归类为 `other`，前端不提交资料分类。
- 所有读取和写入必须沿 `CurrentIdentity → Candidate → CandidateDocument` 校验归属。
- S-05 不解析、下载、删除或主动向 HR/S-10 暴露原文件；删除归属 S-11，后续 Agent 检索和授权交接由后续流程负责。

## 5. 范围 / 非目标

### 当前范围

- 批量附加资料上传；
- PDF、Markdown、JPG、PNG 校验和 10 MB 限制；
- 逐文件成功、幂等成功和失败结果；
- Candidate-owned 资料保存和列表查询；
- 前端真实上传结果与资料列表展示。

### 非目标 / 延期

- 附加资料解析、画像抽取、Embedding 或匹配；
- 文件下载、原文件预览或向 HR 直接展示；
- 资料删除、对象清理和引用关系处理；
- Redis、Celery、Dispatcher、Worker 或异步资料任务；
- 资料版本管理和用户可选资料分类。

## 6. 技术约束

- 数据访问必须经过 Repository；Service 不直接访问 ORM Session 或编写 SQL。
- 对象存储使用现有受控适配器，内部路径和对象键不得进入响应、日志或任务输入。
- 不新增异步任务；上传按文件建立独立事务边界。
- 统一 API 响应为 `{code, msg, data}`。

## 7. 验收标准

- 合法 PDF、Markdown、JPG、PNG 均可上传；单文件超过 10 MB 或格式不支持时逐文件失败。
- 批量上传允许部分成功，失败文件不影响已成功文件。
- 相同 Candidate 重复上传相同内容时返回既有资料，不创建重复业务记录。
- 成功列表只返回资料 ID、名称、文件格式、上传时间和成功状态等安全信息。
- 失败文件不形成 CandidateDocument 持久化记录。
- 其他 Candidate 无法读取或操作当前资料。
- 上传不会创建解析任务，不暴露原文件或内部存储定位。
- `IS-S05-01` 的真实前端路径完成后，前端显示成功提示并看到成功资料进入列表。

## 8. 交付场景

| 项目 | 内容 |
| --- | --- |
| Integration Scenario | [`IS-S05-01`](../../../../../docs/integration/slices/slice-05-candidate-document-upload/integration-scenario.md) |
| Integration Contract | [`IC-S05-CANDIDATE-DOCUMENT-UPLOAD@0.1`](../../../../../docs/integration/slices/slice-05-candidate-document-upload/integration-contract.md) |
| 开发者演示目标 | 求职者批量选择合法和不合规资料，看到 `ready`、成功资料进入列表及失败 Toast 提示 |
| 场景关闭条件 | 真实前端演示、权限/幂等/部分成功测试和问题回归均完成；`IS-S05-01` 已交付 |

## 9. 开发者需裁决事项

无。版本字段、用户资料分类和失败持久化已按本 Slice 设计裁决：不返回版本、不要求用户分类、失败不持久化。
