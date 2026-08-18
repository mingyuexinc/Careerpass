# Integration Scenario：IS-S04-01 求职者上传并解析简历

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `IS-S04-01` |
| 关联 Slice | `S-04` |
| Integration Contract | `IC-S04-RESUME-UPLOAD-PARSE` |
| 场景类型 | `E2E + internal_capability` |
| 交付状态 | `integration_delivered` |

## 1. 交付目标

验证求职者上传一份固定 PDF 后，真实前端显示上传成功并最终显示解析成功；同时通过独立 Capability Acceptance 脚本查看结构化画像结果。

## 2. 固定输入

复用：`careerpass-backend/tests/fixtures/candidate_preparation/resumes/resume_01.pdf`。

固定 PDF 不能包含预置画像、快照或成功状态；Capability Acceptance 必须运行真实解析和业务校验。

## 3. 分层验证

| 层次 | 预期证据 |
| --- | --- |
| Capability Acceptance | 固定 PDF 解析成功，生成 `report.md` 和 `actual.json` |
| Slice Integration | Resume、StoredFileObject、AsyncTaskRun 和 CandidateProfile 状态一致 |
| Infrastructure | Dispatcher/Worker 真实领取、执行和终态提交 |
| E2E | 前端显示上传成功、解析中和解析成功 |

## 4. 最小演示步骤

本节只验证最小 Capability Acceptance，不验证登录、上传接口、数据库、Redis/Celery、Worker 或前端。

在仓库根目录执行以下命令。命令只检查凭据是否存在，不打印凭据值：

```powershell
Set-Location -LiteralPath 'D:\PythonProject\Careerpass'

if (-not ((Test-Path Env:MINERU_API_TOKEN) -or (Test-Path Env:MINERU_API_KEY))) {
    throw '缺少 MINERU_API_TOKEN 或 MINERU_API_KEY'
}
if (-not ((Test-Path Env:QWEN_API_KEY) -or (Test-Path Env:DASHSCOPE_API_KEY))) {
    throw '缺少 QWEN_API_KEY 或 DASHSCOPE_API_KEY'
}

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-resume-parse-capability.ps1
```

脚本固定读取 `careerpass-backend/tests/fixtures/candidate_preparation/resumes/resume_01.pdf`，调用真实 PDF 文本提取和画像结构化链路，并生成验收产物。测试通过后查看最近一次产物：

```powershell
$artifactRoot = Join-Path (Get-Location) 'careerpass-backend/tests/acceptance/s04_resume_parse/delivery-acceptance-results'
$latest = Get-ChildItem -LiteralPath $artifactRoot -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $latest) {
    throw '未找到 Capability Acceptance Artifact'
}

Get-Content -LiteralPath (Join-Path $latest.FullName 'report.md')
Get-Content -LiteralPath (Join-Path $latest.FullName 'actual.json')
```

该固定 PDF 的预期自动断言为 `passed: true`、`parse_status: succeeded` 和 `matching_ready`，且姓名、手机号或邮箱、教育经历、工作经历或项目经历均有效，两段正式工作公司不同，工作年限已从非实习时间段派生。`actual.json` 只包含经结构化校验的画像字段，联系方式由测试代码脱敏，不包含完整简历原文。

本节命令执行后，由开发者将实际结果和其它问题填写到下表；以下记录为本次实际执行结果，不作为执行前的预填值：

| 记录编号 | 执行结果 | 实际结果 | 其它问题 |
| :------: | -------- | --------------- | -------- |
|    1     | 通过 | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-resume-parse-capability.ps1` 生成 `20260815T155611Z-fc83327a`；固定 PDF 的必需字段、工作年限和两段工作公司区分断言均通过 | 无 |

## 5. 问题与整改

本次开发者验收未报告其它问题；此前最终判定失败的验收产物不作为交付证据，已删除。

| 记录编号 | 问题类型 | 原因与分析 | 整改结果 | 验收结果 |
| :------: | :------: | ---------- | -------- | -------- |
|    1     | 无 | 无 | 无 | 开发者裁定通过 |

## 6. 关闭条件

- Capability Acceptance 自动断言通过并生成成功 Artifact；
- Slice Integration、适用 Infrastructure 和前端状态交接证据已完成；
- 开发者已审阅结果并裁定通过；
- 最终状态：`integration_delivered`。
