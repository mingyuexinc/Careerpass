# Integration Contract：S-05 求职者资料上传

| 项目 | 内容 |
| --- | --- |
| Contract ID | `IC-S05-CANDIDATE-DOCUMENT-UPLOAD` |
| 版本 | `0.1` |
| 关联 Slice | `S-05` |
| 关联 Integration Scenario | `IS-S05-01` |
| Producer | S-05 后端资料上传能力 |
| Consumer | 求职者资料上传页 |
| 状态 | `locked` |

## 1. 用户场景与边界

- 角色：已登录求职者。
- 触发：在资料页选择一份或多份附加资料后立即上传。
- 结果：逐文件显示 `ready`、`success` 或 `failed`；成功资料进入列表。
- 不包含：解析、画像、下载、删除、HR 查看、S10 主动读取和外部副作用。
- 业务依据：S05 `slice-spec.md`、业务基线 `BF-FLOW-014/015`、`BF-RULE-020/021/022/023`、`BF-STATE-015`。

## 2. 请求契约

| 项目 | 约定 |
| --- | --- |
| 方法与路径 | `POST /api/v1/candidate_documents` |
| 身份与授权 | 服务端确认 Candidate，并校验所有资料归属当前 Candidate |
| 请求格式 | multipart/form-data，字段 `files`，至少一份 |
| 文件限制 | `.pdf`、`.md`、`.jpg`、`.png`；每个文件不超过 10 MB |
| 资料分类 | 不由前端提交，后端固定保存为 `other` |
| 幂等 | 同一 Candidate + 相同内容摘要返回既有资料；可选 `Idempotency-Key` 只辅助请求重放 |

## 3. 响应契约

所有响应遵循 `{code, msg, data}`。

`data.results` 按输入文件顺序返回：

| 字段 | 说明 |
| --- | --- |
| `file_name` | 用户提交的文件名 |
| `result` | `created`、`duplicate` 或 `failed` |
| `candidate_document_id` | 成功或重复时的资料 ID，失败为空 |
| `file_type` | `pdf`、`md`、`jpg` 或 `png` |
| `upload_status` | 成功/重复为 `success`，失败为 `failed` |
| `uploaded_at` | 成功或重复资料的时间，失败为空 |
| `failure_code` | 失败时的安全分类，成功为空 |

| 场景 | HTTP / code | 前端结果 |
| --- | --- | --- |
| 至少一个文件成功 | `200 / 200` | 显示当前成功提示，成功资料进入列表 |
| 全部重复 | `200 / 200` | 仍按成功提示处理，不新增资料 |
| 批量部分失败 | `200 / 200` | 成功资料进入列表，失败文件不进入成功结果区域，批次完成后显示一次性 error Snackbar/Toast |
| 请求无文件或身份无效 | `400/401` | 保留选择结果并显示当前错误反馈 |

## 4. 列表契约

`GET /api/v1/candidate_documents` 仅返回当前 Candidate 的成功资料，支持 `page`、`page_size`。

列表项包含：`candidate_document_id`、`name`、`file_type`、`upload_status=success`、`created_at`。不包含版本、正文、对象键、路径或下载地址。

## 5. 状态、错误与安全

```text
前端选择文件 → ready
  → 上传并保存成功 → success
  → 格式/大小/存储/事务失败 → failed
```

- `ready` 由前端管理，后端不持久化该状态。
- `failed` 文件不形成正式资料记录；失败文件不进入成功上传结果区域或持久页面状态，前端在批次完成后显示一次性 error Snackbar/Toast，自动消失且不提供重试按钮。
- `created` 和 `duplicate` 都显示为成功；失败提示沿用当前前端错误反馈机制。
- 不返回文件正文、对象键、内部路径、原始异常或敏感信息。
- 契约变更必须回退 Slice Design，并同步后端 Schema、前端类型、Mock 和 Scenario。
