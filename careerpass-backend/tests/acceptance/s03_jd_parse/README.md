# S-03 岗位 JD 解析交付目标测试

本目录承载 S-03 测试代码；Capability Acceptance 生成结果放在本目录的 `delivery-acceptance-results/`，开发者重点关注该结果目录。

| 目录/文件 | 语义 |
| --- | --- |
| `harness/` | S03 测试 Harness、测试定义、Factory、Repository 和 Expected Manifest；不存放通用 JD 原文件 |
| `unit/` | S-03 JD 解析专属单元测试 |
| `delivery-acceptance-results/<run-id>/` | 每次 Capability Acceptance 生成的 `report.md` 和 `actual.json`，用于开发交付审阅；该目录内容由测试命令生成，不作为测试定义 |

Capability Acceptance 只验证“固定 JD 文本 → 真实解析结果”；直接持久化、Redis/Celery、跨 Slice 和 E2E 由对应专项测试负责，不混入核心能力自测。

从仓库根目录执行核心能力自测：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\careerpass-backend\scripts\test-jd-parse-capability.ps1
```

该命令不要求 PostgreSQL、Redis、Celery 或 S03 API 已启动。

001、002 岗位 JD 是通用真实演示数据，固定存放在 [`tests/fixtures/job_descriptions/`](../../fixtures/job_descriptions/)，不得移动或复制到本目录。
