# Integration Contract：S-03 JD 信息抽取

> 本契约锁定 S-03 解析结果的跨 Slice 交接语义和纯内部验证 API；实现细节、代码结构和迁移 revision 由后端 S-03 Technical Design 承接。

| 项目 | 内容 |
| --- | --- |
| Contract ID | `IC-S03-JD-EXTRACTION` |
| 版本 | `0.2` |
| 关联 Slice | `S-03` |
| 关联 Integration Scenario | `IS-S03-01` |
| Producer | S-03 JD 解析能力 |
| Consumer | S-08 岗位匹配能力、开发者验证程序 |
| 状态 | `locked` |

## 1. 已锁定的交付语义

- S-03 的交付结果是经过校验的结构化 `fields`，不是 `raw_sections`；
- `fields` 是 `ParsedJobDescriptionSnapshot` 对外提供的主要业务结果，字段集合允许超过当前五项核心字段；
- `raw_sections` 作为原文保真、未知标题保留和结果追溯数据保存，不作为 S-08 的主要匹配输入；
- `fields` 中的可匹配值必须经过确定性结构化和业务校验；当前版本不生成大模型摘要、职位同义归一或其他大模型语义扩展；
- 未识别的固定标题不得丢弃，可进入 `additional_fields` 或等价的扩展字段区域；
- `fields` 的参考结构见 [`fields.schema.json`](fields.schema.json)，该文件是对比模板，不替代 S-03 Technical Design 的最终 Schema；
- S-08 只消费解析成功且 `matching_ready` 的 `fields`，并在匹配运行时生成自己的不可变匹配输入快照；
- S-02 上传成功不表示 S-03 解析成功，S-03 失败时不得返回可供 S-08 使用的成功 `fields`。
- 五项核心字段是当前匹配所需的必填字段；字段缺失不转化为结构校验失败，而是作为核心字段缺失失败语义标记为 `matching_not_ready`，且不创建快照。

## 2. 解析调用边界

开发者调用 S-03 提供的纯内部验证 API，提交受控本地存储路径 `local_path`，由 S-03 从该路径读取真实 `.md` JD。该 API 不属于前端公开上传接口，不得接收任意路径，也不得直接提交预构造 `fields`。

内部验证 API 采用“提交任务 + 查询任务”模式：提交接口返回 `task_id` 和 `queued/running` 状态；查询接口根据 `task_id` 返回当前状态，解析成功后在同一查询结果中返回 `fields`。当前锁定的接口为 `POST /internal/v1/s03/job-description/parses` 和 `GET /internal/v1/s03/job-description/parses/{task_id}`；最终结果必须遵循统一响应结构 `{code, msg, data}`，并能观察到：

```text
queued/running  → 仅返回任务状态，不返回 fields
parse_succeeded + matching_ready → ParsedJobDescriptionSnapshot.fields
parse_failed    → 受控失败分类，不产生可用 fields
core fields missing → parse_failed + matching_not_ready，不创建快照
```

本地路径只允许解析受控存储根目录内的文件；路径不得进入公开响应、异步任务持久化字段、普通日志或追踪。当前 S-03 只定义三种失败语义：临时技术失败、输入不可用、核心字段缺失。结构校验失败不属于当前受控演示版本的 JD 失败分支。

## 3. 结果契约

结果至少包含：

| 字段 | 语义 |
| --- | --- |
| `job_id` | 归属的 Job 标识 |
| `snapshot_id` | 成功解析快照标识 |
| `parse_status` | `succeeded` 或 `failed` |
| `matching_status` | 成功时为 `matching_ready`；核心字段缺失失败时为 `matching_not_ready` |
| `failure_semantics` | 临时技术失败、输入不可用或核心字段缺失 |
| `failure_reason` | 失败的脱敏具体原因；临时技术失败重试耗尽时为 `retry_exhausted` |
| `missing_core_fields` | 缺失的核心字段标识；无缺失时为空 |
| `schema_version` | `fields` 结构版本 |
| `fields` | 结构化岗位字段，符合 [`fields.schema.json`](fields.schema.json) |

`fields` 的字段值可以同时保留 `raw` 和确定性归一化值；归一化不得覆盖原始值。`raw_sections` 不作为本 Contract 的默认响应主体，不得迫使 S-08 重新解析 JD。

## 4. S-08 交接约束

- S-08 只接收解析成功且 `matching_ready` 的快照；
- S-08 不读取原始 Markdown，也不直接消费未校验的模型输出；
- S-08 启动匹配时锁定实际使用的 JD `fields`、候选人画像、求职目标和 `algorithm_version`；
- S-03 不负责生成匹配分数、推荐理由或投递结果；
- 当前版本不因大模型语义解析缺失而阻断 S-03 或 S-08，职位同义归一和长文本语义摘要不属于当前 Contract。

## 5. 安全与失败边界

- 不返回内部存储路径、对象键、原始异常或凭证；
- 原始 JD 正文只在解析所需范围内读取，不进入普通日志或追踪；
- 解析成功结果必须经过 Schema 和业务规则校验，五项核心字段有效后才能创建快照；
- 临时技术失败表示本次执行尝试失败，不是立即终态；任务自动重试，重试耗尽后进入 `failed`，失败原因标记为 `retry_exhausted`；
- 输入不可用立即进入 `failed`；核心字段缺失立即进入 `failed + matching_not_ready`，不创建快照；
- 重试、幂等和任务终态由 S-03 Technical Design 锁定。

## 6. 解析失败后的再次上传

| 场景 | 处理 |
| --- | --- |
| 原 Job 未删除，解析失败后再次上传相同 JD | 复用原 Job，重建解析任务 |
| 原 Job 已删除，再次上传相同 JD | 不复用已删除 Job，创建新 Job |
| 再次上传内容不同的 JD | 创建新 Job |
| 原解析任务仍在执行 | 保持任务幂等，不重复创建任务 |

当前演示不考虑已有旧快照再次解析失败后的清除或保留语义；最小演示只验收成功解析结果，失败语义由后端接口自测覆盖。

## 7. 锁定记录

| 日期 | 变化 | 影响 | 回退 Gate | 结论 |
| --- | --- | --- | --- | --- |
| 2026-08-14 | 明确 S-03 以 `fields` 作为主要解析交付结果，`raw_sections` 作为保真数据；当前不实现大模型语义解析 | S-03、S-08、fields Schema | S-03 Slice Design / Readiness Check | 已由真实 API 和 `IS-S03-01` 核对 |
| 2026-08-14 | 明确当前 S-03 只处理临时技术失败、输入不可用、核心字段缺失三种语义；核心字段缺失以 `parse_failed + matching_not_ready` 表达且不创建快照；结构校验失败不纳入当前 JD 演示分支 | S-03、S-08、fields Schema | S-03 Slice Design / Readiness Check | 已由迁移、任务状态和真实场景核对 |
| 2026-08-14 | 明确内部验证 API 使用本地存储路径提交异步任务并通过查询接口返回成功 `fields`；临时技术失败自动重试，核心字段缺失失败且不创建快照；未删除失败 Job 重建任务，已删除 Job 不复用 | S-02、S-03、S-08 | S-03 Slice Design / Readiness Check | S-02/S-03 Contract；真实任务链和 `IS-S03-01` 已通过 |
