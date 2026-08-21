# Integration Scenario：S11-01 候选人简历删除

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `IS-S11-01` |
| 关联 Slice | S11 业务资料删除 |
| Integration Contract | `./integration-contract.md`，`IC-S11-BUSINESS-MATERIAL-DELETION@0.1` |
| 场景类型 | `frontend_visible` |
| 交付状态 | `integration_delivered` |

## 1. 交付目标

候选人在资料页删除当前简历；页面、当前简历状态和后续上传行为与 Contract 一致。

## 2. 前置条件与数据

- 已登录 Candidate；
- 准备 Resume 状态：`processing`、`succeeded + matching_ready`、`succeeded + matching_not_ready`、`failed`；
- 准备 Agent 未启动、运行中、已结束三种状态；
- 准备两份历史简历，验证删除当前简历后不自动回退；
- 自动化目录：`careerpass-backend/tests/unit/`；
- 自动化入口：`test_s11_business_resource_deletion_api.py`；执行命令：`uv run pytest tests/unit/test_s11_business_resource_deletion_api.py -o addopts='-q'`（从 `careerpass-backend` 执行）；
- 结果目录：`docs/integration/slices/slice-11-business-material-deletion/artifacts/IS-S11-01-acceptance/`。
- 结果文件：`report.md`、`actual.json`、`expected-manifest.json`；结果文件仅由实际演示/自动化执行生成。
- 依赖场景：S01 登录、S04 简历解析、S07 Agent 启动条件；不依赖 S10。

## 3. 步骤与预期

| 步骤 | 操作 | 预期系统结果 | 预期页面结果 |
| --- | --- | --- | --- |
| 1 | 进入资料页并查看当前简历 | 返回当前简历及解析状态 | 展示当前简历卡片 |
| 2 | 删除 `succeeded` 或 `failed` 的当前简历且 Agent 未启动 | 逻辑删除并写一条审计 | 卡片消失，当前简历空状态 |
| 3 | 删除 `processing` 简历或 Agent 已启动时的简历 | 返回 409，状态不变 | 删除按钮禁用或展示受控原因 |
| 4 | 分别验证 `matching_ready` 与 `matching_not_ready` 的终态简历 | 两种匹配资格均可删除 | 删除按钮状态一致 |
| 5 | 删除当前简历后查看历史简历并上传新简历 | 历史简历不自动成为当前；新形成的简历成为当前 | 新简历成为当前 |
| 6 | 重复删除同一简历 | 返回幂等成功，不新增审计 | 不重复提示，列表保持不变 |

## 4. 最小演示验证结果

- 开发者已完成正式前端删除路径验证，当前简历删除后页面进入无当前简历状态，历史简历不自动回退，新上传简历成为当前简历。
- `processing`、Agent 已运行/已结束等不可删除状态保持原列表；`succeeded + matching_ready`、`succeeded + matching_not_ready` 和 `failed` 的删除资格符合 Contract。
- 重复删除返回幂等结果，不新增审计事件。
- 自动化回归：后端单元测试 `255 passed`；前端类型检查通过，前端测试 `72 passed`。
- 脱敏产物：[`report.md`](artifacts/IS-S11-01-acceptance/report.md)、[`actual.json`](artifacts/IS-S11-01-acceptance/actual.json)。

## 5. 关闭结论

- 自动化回归、正式前端演示和开发者审阅已完成；当前状态：`integration_delivered`。
