# Slice：S-04 简历上传与解析

> 当前阶段：Close
>
> 本 Slice 已完成开发交付；前端只展示上传和解析处理结果，匹配资格作为后端交接状态保留。开发者已裁定最小核心能力验证通过。

## 1. 目标

交付两个结果：

1. 求职者一次上传一份文本型 PDF，前端显示上传成功、解析中和解析终态；
2. 开发者运行固定 PDF 能力脚本，查看结构化画像并验证核心解析能力。

## 2. 输入与输出

| 项目 | 约束 |
| --- | --- |
| 输入身份 | 已登录且服务端确认的 Candidate |
| 上传粒度 | 一次请求只能上传一份 PDF |
| 文件范围 | 文本型 PDF；扫描件、图片型 PDF、加密 PDF 和密码保护 PDF 不在范围内 |
| 成功结果 | Resume 进入 `succeeded`，形成已校验 CandidateProfile，并计算 `matching_ready/not_ready` |
| 失败结果 | Resume 进入 `failed`，保留受控失败分类，不形成半成品画像 |
| 前端结果 | 展示文件处理状态，不展示画像字段、联系方式、教育内容或匹配资格详情 |

## 3. 业务规则

本 Slice 使用 `BF-OBJECT-001`、`BF-OBJECT-009`、`BF-OBJECT-010`、`BF-FLOW-002`、`BF-FLOW-011`、`BF-FLOW-013`、`BF-RULE-003`、`BF-RULE-004`、`BF-RULE-005`、`BF-RULE-010`、`BF-RULE-012`、`BF-RULE-013`、`BF-RULE-018`、`BF-RULE-019`、`BF-STATE-009`、`BF-STATE-014` 和 `BF-SCOPE-016`。

- 一个 Candidate 可以拥有多份 Resume；不同内容的 PDF 创建独立 Resume。
- 同一 Candidate 重复上传相同 PDF 时按内容摘要幂等复用已有 Resume、解析状态和画像，不创建新版本或新的解析任务。
- Resume 主状态为 `processing → succeeded/failed`。
- 解析成功与匹配资格分开表达；缺少最小业务字段时为 `parse_succeeded + matching_not_ready`，不阻断解析成功，但不得启动 Agent。
- 最小业务字段为姓名、手机号或邮箱、教育经历，以及工作经历或项目经历至少一项。
- 目标岗位、技能、工作年限、期望地点和期望薪资等字段均为可选字段。
- 工作年限不由模型推测，按 `BF-RULE-019` 从非实习工作时间段派生。
- 上传、解析和画像读取必须校验当前 Candidate 归属。
- S-04 不创建求职目标、不启动 Agent、不执行匹配、不创建投递记录。

## 4. 范围与非目标

### 当前范围

- 单 PDF 上传；
- 内容摘要幂等复用；
- 异步解析任务交接和状态查询；
- 结构化画像校验和匹配资格判定；
- 前端真实上传与解析状态展示；
- 固定 PDF Capability Acceptance。

### 非目标

- 扫描件、图片型 PDF、加密 PDF 和密码保护 PDF；
- 简历正文下载、复杂文件中心和资料删除；
- 画像字段在本次前端页面展示；
- 求职目标、Agent、匹配、投递和外部招聘平台副作用；
- 用 Capability Acceptance 代替真实异步链路或前端 E2E。

## 5. 验收标准

- 求职者只能提交一份 PDF；非 PDF 被拒绝；
- 合法 PDF 显示上传成功并进入解析中；
- 解析成功显示解析成功；解析失败显示解析失败；
- 相同 Candidate 重复上传相同 PDF 时复用已有 Resume，不创建新版本或新任务；
- 不同 PDF 可形成不同 Resume；
- 成功画像只在 Schema 和业务规则校验通过后写入；
- 最小业务字段完整时判定 `matching_ready`；缺失时判定 `matching_not_ready`；
- 可选字段缺失不阻断解析成功；
- 前端不展示画像内容和匹配资格详情；
- 固定 PDF 能力脚本生成可审阅的 `report.md` 和 `actual.json`；
- 不暴露完整简历原文、内部路径、模型原始响应或不必要敏感信息。
