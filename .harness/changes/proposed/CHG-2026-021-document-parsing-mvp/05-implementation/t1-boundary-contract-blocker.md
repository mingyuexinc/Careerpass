# T1 边界契约核对记录（历史证据；当前治理迁移待复核）

> 本记录保留旧阶段的阻塞分析，不构成当前阶段 4/5 授权。当前唯一契约来源为 `.harness/contracts/resume-parse-request-v1.yaml`；在联合锁定前不得据本文件恢复实现。

## 结论

原 T1 阻断已解除，状态调整为“待门禁复核”。开发者已确认“跨模块契约交接”不等同于“资料准备模块主动调用解析模块”。本次仅修订需求、方案和任务表述，未修改业务代码、数据库、接口或外部依赖。

## 已核对通过的边界

- `ResumeParseRequestV1` 为固定 `v1` 结构，仅包含 `candidate_id`、`resume_id` 和 `task_version`。
- Schema 使用 `extra="forbid"`，不接受路径、URL、文件正文、对象键、MCP 参数、模型参数或自由指令。
- `DocumentParsingRepository.get_profile(candidate_id, resume_id)` 同时按候选人和简历归属过滤。
- 画像查询通过已认证 `CurrentIdentity.candidate_id` 进入 Service/Repository，不接受客户端指定候选人身份。
- 简历解析模块没有新增独立解析触发 API；成功/失败查询沿用既定受控接口和 `{code,msg,data}` 响应包络。

## 原阻断项及解除说明

| 来源 | 当前裁决/实现 | 与另一侧的冲突 |
| --- | --- | --- |
| CHG-2026-021 | G2 在资源事务中创建/复用 queued `AsyncTaskRun`，G3 通过 `ResumeParseRequestV1@v1` 消费既有任务 | 当前治理裁决；G3 不创建第二个任务，也不调用 G2 内部实现 |
| CHG-2026-020 | G2 不调用解析 Service、Dispatcher、Worker 或模型能力 | 与上述交接方式兼容 |
| 当前实现 | 上传与资料记录边界已存在；后续代码任务需补齐既定契约交接的实际实现与联调证据 | 不得通过临时 Service 直连解决 |

解除后的正式边界为：G2 在同一事务中创建/复用固定版本 `ResumeParseRequestV1@v1` 对应的 queued `AsyncTaskRun`，不调用 G3 内部实现；G3 负责消费既有任务并执行解析。契约交接的具体实现仍须在联合锁定、阶段 4 和阶段 5 门禁后开发，不得临时新增未裁定的事件、API 或隐式扫描机制。

## 后续门禁动作

1. 由开发者复核修订后的 CHG-020/021 需求与方案。
2. 重新确认阶段 1 的跨模块契约边界，再复核阶段 2–4 的既有证据是否仍适用。
3. 阶段 5 仅从 T1 的契约交接实现/验证开始；不得直接进入 Worker、MinerU 或 Qwen 链路。

## 安全与证据边界

本记录只包含模块、类、接口和契约级信息；未记录简历正文、对象键、路径、凭证、模型响应或异常堆栈。
