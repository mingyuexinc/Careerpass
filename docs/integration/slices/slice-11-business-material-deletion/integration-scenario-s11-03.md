# Integration Scenario：S11-03 HR 岗位 JD 删除

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `IS-S11-03` |
| 关联 Slice | S11 业务资料删除 |
| Integration Contract | `./integration-contract.md`，`IC-S11-BUSINESS-MATERIAL-DELETION@0.1` |
| 场景类型 | `frontend_visible` |
| 交付状态 | `integration_delivered` |

## 1. 交付目标

HR 在岗位 JD 页面删除自己拥有且解析已结束、匹配尚未开始的岗位；删除后岗位列表和空状态正确更新。

## 2. 前置条件与数据

- 已登录 HR；
- 准备 JD 解析 `queued`、`running`、`succeeded`、`failed` 状态；
- 准备一个已经产生 Match/Application 的岗位；
- 准备另一 HR 所有的岗位用于归属校验；
- 自动化目录：`careerpass-backend/tests/unit/`；
- 自动化入口：`test_s11_business_resource_deletion_api.py`；执行命令：`uv run pytest tests/unit/test_s11_business_resource_deletion_api.py -o addopts='-q'`（从 `careerpass-backend` 执行）；
- 结果目录：`docs/integration/slices/slice-11-business-material-deletion/artifacts/IS-S11-03-acceptance/`。
- 结果文件：`report.md`、`actual.json`、`expected-manifest.json`；结果文件仅由实际演示/自动化执行生成。
- 依赖场景：S01 登录、S02/S03 岗位上传与解析、S08 匹配与投递。

## 3. 步骤与预期

| 步骤 | 操作 | 预期系统结果 | 预期页面结果 |
| --- | --- | --- | --- |
| 1 | 删除解析成功或失败且未匹配的岗位 | 逻辑删除、移除 S-03 当前快照并写审计 | 岗位从列表消失 |
| 2 | 删除解析中或已匹配岗位 | 返回 409，岗位保持可见 | 删除按钮禁用或展示受控原因 |
| 3 | 使用非归属 HR 删除岗位 | 返回 403 | 不泄露岗位详情 |
| 4 | 删除最后一份可用岗位 | 返回成功 | 页面展示岗位空状态 |
| 5 | 重复删除同一岗位 | 返回幂等成功，不新增审计 | 不重复提示，列表保持不变 |

## 4. 最小演示验证结果

- 开发者已完成真实 HR 前后端验证：受控 HR 登录成功，岗位列表读取成功。
- 目标岗位删除返回 HTTP 200、`deleted=true`；删除后列表总数由 7 条变为 6 条，目标岗位不再返回。
- 解析中、已发起匹配和非归属 HR 的删除边界由状态矩阵、权限测试和前端禁用逻辑覆盖。
- 后端迁移 `20260821_0018` 已执行，Backend/Worker/Dispatcher 健康运行；前端删除不再弹出确认窗口。
- 脱敏产物：[`report.md`](artifacts/IS-S11-03-acceptance/report.md)、[`actual.json`](artifacts/IS-S11-03-acceptance/actual.json)。

## 5. 关闭结论

- 自动化回归、正式前端演示和开发者审阅已完成；当前状态：`integration_delivered`。
