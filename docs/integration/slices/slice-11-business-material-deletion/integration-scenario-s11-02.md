# Integration Scenario：S11-02 附加资料删除与附件保留

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `IS-S11-02` |
| 关联 Slice | S11 业务资料删除、S10-02 资料附件交付 |
| Integration Contract | `./integration-contract.md`，`IC-S11-BUSINESS-MATERIAL-DELETION@0.1` |
| 场景类型 | `frontend_visible` |
| 交付状态 | `integration_delivered` |

## 1. 交付目标

候选人可以在 Agent 任意生命周期删除已保存附加资料；删除后新的资料检索不可命中，删除前已创建的 S10-02 附件在 7 天内继续可下载。

## 2. 前置条件与数据

- 已登录 Candidate；
- 已保存一个未发送附件的附加资料和一个已创建 `MessageAttachment` 的附加资料；
- 准备 Agent 未启动、运行中、已结束状态；
- 已完成 S10-02 当前 Conversation 和 HR 访问条件；
- 自动化目录：`careerpass-backend/tests/unit/`；
- 自动化入口：`test_s11_business_resource_deletion_api.py`；执行命令：`uv run pytest tests/unit/test_s11_business_resource_deletion_api.py -o addopts='-q'`（从 `careerpass-backend` 执行）；
- 结果目录：`docs/integration/slices/slice-11-business-material-deletion/artifacts/IS-S11-02-acceptance/`。
- 结果文件：`report.md`、`actual.json`、`expected-manifest.json`；结果文件仅由实际演示/自动化执行生成。
- 依赖场景：S01 登录、S05 附加资料上传、S10-02 附件交付。

## 3. 步骤与预期

| 步骤 | 操作 | 预期系统结果 | 预期页面/产物 |
| --- | --- | --- | --- |
| 1 | 删除已保存附加资料 | 逻辑删除并写审计 | 资料列表移除 |
| 2 | 再次请求 S10-02 新资料检索 | 删除资料不参与匹配 | 不创建新附件 |
| 3 | 下载删除前已发送附件 | 来源资料删除不影响附件有效期 | 7 天内下载成功 |
| 4 | 重新上传相同内容 | 创建新的业务资料，不复用删除记录 | 新资料重新出现在列表 |
| 5 | 重复删除同一资料 | 返回幂等成功，不新增审计 | 不重复提示，列表保持不变 |

## 4. 最小演示验证结果

- 开发者已完成附加资料删除路径验证，删除后资料从当前列表消失，新的资料检索不再命中。
- 删除前已创建的 `MessageAttachment` 不因来源资料逻辑删除而失效，继续按 7 天有效期规则处理。
- 相同内容重新上传形成新的业务资料；重复删除保持幂等且不重复审计。
- S10-02 既有附件交付回归通过；后端单元测试 `255 passed`，前端测试 `72 passed`。
- 脱敏产物：[`report.md`](artifacts/IS-S11-02-acceptance/report.md)、[`actual.json`](artifacts/IS-S11-02-acceptance/actual.json)。

## 5. 关闭结论

- 自动化回归、S10-02 联调、正式前端演示和开发者审阅已完成；当前状态：`integration_delivered`。
