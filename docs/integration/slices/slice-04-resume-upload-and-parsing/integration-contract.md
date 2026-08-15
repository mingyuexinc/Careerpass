# Integration Contract：S-04 简历上传与解析

| 项目 | 内容 |
| --- | --- |
| Contract ID | `IC-S04-RESUME-UPLOAD-PARSE` |
| 关联 Slice | `S-04` |
| Producer | S-04 简历上传与解析 |
| Consumer | 求职者前端、S-06/S-07 后端能力 |
| 状态 | `locked` |

## 1. 业务交接

```text
单份 PDF 上传
→ upload accepted + processing
→ parse succeeded / failed
→ parse succeeded 时另行得到 matching_ready / matching_not_ready
```

`parse_status` 与 `matching_readiness` 不互相替代。前端上传页只展示上传和解析处理结果；匹配资格和结构化画像不进入页面展示。

## 2. 请求与响应边界

### `POST /api/v1/resumes`

- 已认证 Candidate；
- multipart `file` 只能包含一个 PDF；
- 合法新文件返回 `resume_id` 和 `processing`；
- 相同内容重复上传返回已有 `resume_id` 和当前解析状态；
- 不创建新版本或重复任务；
- 不返回画像、简历正文、内部路径、对象键或模型原始响应。

### `GET /api/v1/resumes`

- 返回当前 Candidate 的 Resume 状态列表；
- 前端使用它观察 `processing/succeeded/failed`；
- 不返回画像字段。

## 3. 前端状态

| 状态 | 页面表现 |
| --- | --- |
| 上传成功 | 显示上传成功并进入解析中 |
| `processing` | 显示解析中，禁止重复提交 |
| `succeeded` | 显示解析成功 |
| `failed` | 显示解析失败 |

页面可以显示文件名和处理状态，但不显示姓名、联系方式、教育、工作/项目经历、匹配资格或完整正文。

## 4. 后端交接

- 成功画像必须经过 Schema 和业务字段校验；
- `matching_ready/not_ready` 仅供后端后续 Slice 使用；
- S-06/S-07 不读取原始 PDF 或未校验解析输出；
- 所有资源读取必须通过 Candidate 归属链校验。
