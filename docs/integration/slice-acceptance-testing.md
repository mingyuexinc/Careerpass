# Internal Capability Slice 测试与验收规范

## 1. 适用范围

本规范适用于没有前端页面直接展示结果的内部能力 Slice，例如岗位 JD 解析、简历解析和匹配结果生成。

这类 Slice 的 `Integration Scenario` 允许以稳定内部入口、任务结果和 Acceptance Artifact 作为交付证据；场景必须声明采用 `Capability Acceptance`、`Slice Integration Test`、`Infrastructure Test`、`Cross-Slice Integration Test` 还是 `E2E Test`。有前端可展示结果的 Slice 仍须按真实前端路径验收。两类场景都必须遵守对应的 Slice 规格、Integration Contract 和 Handoff Contract。

## 2. 验收边界

同一个交付目标的测试代码必须归属于 `tests/` 下的同一个交付目标测试文件夹，包括 Acceptance Test、Factory、Repository、Unit Test 和 Expected Manifest。岗位 JD 等通用真实演示数据继续存放在 `tests/fixtures/job_descriptions/`，不得为了某个 Slice 复制或移动；Expected Manifest 不得放在通用岗位数据目录中。测试运行生成的 `report.md` 和 `actual.json` 属于运行产物，放在该交付目标测试文件夹下明确命名的结果目录中，并作为开发者重点审阅对象。

Internal Capability Slice 的交付目标首先是一个明确的核心业务能力。工程链路只纳入该能力进入系统所需的最小 Integration Readiness，不把共享基础设施和完整上下游流程自动纳入核心能力验收。

测试按以下边界分别承担责任：

- `Capability Acceptance` 从当前 Slice 的核心业务输入开始，到核心业务输出结束；例如 JD 文本进入解析器，得到结构化解析结果。该测试不包含数据库、Redis、Celery、登录、上传、匹配等非核心链路；
- `Slice Integration Test` 验证当前 Slice 自身的直接集成，例如数据库持久化、Repository、事务和当前 Slice 的正式内部入口；
- `Infrastructure Test` 验证 Redis、Celery、Dispatcher、Worker 等公共机制本身；
- `Cross-Slice Integration Test` 验证两个 Slice 之间的真实数据和状态交接；
- `E2E Test` 验证从用户入口到最终业务结果的完整流程。

其中，Integration Scenario 可以把稳定内部入口、任务结果和 Acceptance Artifact 作为内部能力 Slice 的交付证据，但必须明确本次场景验证的是上述哪一层。单个 Slice 的 Capability Acceptance 不得因为共享基础设施或上下游流程存在就扩大边界。

Slice Acceptance Test 从当前 Slice 的契约输入开始，到当前 Slice 的契约输出结束：

- 上游 Slice 只提供可信前置条件；测试通过 Fixture、Factory 或 Setup 构造所需资源，不重复执行登录、上传等完整上游流程；
- Capability Acceptance 不得用预置的当前 Slice 输出替代被测核心逻辑；输入 Fixture 可以固定，核心解析、校验和业务结果必须执行真实实现；
- 持久化、状态迁移、任务和内部入口等直接集成由 Slice Integration Test 单独验证，不得把其通过结果写成 Capability Acceptance 的通过条件；
- Redis、Celery、Dispatcher、Worker 等公共机制由 Infrastructure Test 验证；未纳入当前测试时可以直接调用核心处理逻辑，但不得据此宣称基础设施链路已交付；
- 下游 Slice 由 Cross-Slice Integration Test 验证；E2E 测试负责完整用户流程；
- Fixture 必须通过受控 Factory、Repository 或正式用例构造，满足资源归属、状态机、唯一性和可读性约束，不得用任意 SQL 或绕过业务规则的数据库插入代替前置数据。

## 3. 测试分层

| 层级 | 目标 | 典型范围 |
| --- | --- | --- |
| Unit / Service Test | 验证局部规则 | 解析、Schema、状态迁移、归属、幂等分支 |
| Capability Acceptance | 验证当前 Slice 的核心业务能力 | 固定 Fixture、真实核心逻辑、核心业务输出和 Expected / Actual |
| Slice Integration Test | 验证当前 Slice 的直接集成 | 内部入口、Repository、数据库、事务、持久化和当前 Slice 状态 |
| Infrastructure Test | 验证公共工程机制 | Redis、Celery、Dispatcher、Worker、租约、重试和消息消费 |
| Cross-Slice Integration Test | 验证 Slice 间衔接 | Producer 输出被 Consumer 正确读取和解释 |
| E2E Test | 验证完整用户流程 | 登录、上传、处理、匹配或最终页面结果 |

单 Slice 的 Capability Acceptance、Slice Integration Test 和 Infrastructure Test 可以分别运行；它们不互相冒充。Cross-Slice 和 E2E 测试应保持少量且针对高风险交接或主流程。

## 4. 自动验收与人工产物

每个内部能力 Slice 应为开发者提供 Capability Acceptance 的稳定短命令入口，例如 `make test-jd-parse` 或项目约定的等价命令。该命令只负责核心能力的输入、执行、自动断言和 Acceptance Artifact；开发者不应手工拼接长命令或查询数据库完成核心能力自测。其它测试层可以拥有各自的专项命令，不要求由同一个命令承担。

自动断言至少覆盖：

- 契约 Schema、状态和错误语义；
- 业务核心字段的固定 Expected / Actual 对比，而不只是非空检查；
- 核心业务输出的固定 Expected / Actual 对比；
- 对应测试层明确声明的直接集成、基础设施或交接条件。Capability Acceptance 不自动断言数据库、任务、Redis/Celery 或下游可读性。

测试还必须生成可人工审阅的 Acceptance Artifact，至少包含 `report.md` 和完整的 `actual.json`。Capability Acceptance 产物展示 Fixture 标识、真实输入摘要、实际核心输出、关键断言和 Expected / Actual 对比；其它测试层的产物再展示其负责的任务、持久化、基础设施或交接证据。产物不得包含凭证、未脱敏简历或联系方式、完整内部路径、原始模型响应或不必要的敏感原文。

Acceptance Artifact 是交付证据，不是新的业务契约；业务字段、状态和错误语义仍以 Slice 和 Integration Contract 为准。

## 5. 场景关闭

内部能力 Slice 的 Integration Scenario 只有在以下条件同时满足时才能关闭：

- 当前场景声明的测试层执行成功；
- 该层的自动断言通过并生成对应 Acceptance Artifact；
- 开发者已审阅核心业务结果或该层负责的交付证据，并在场景文档中记录验收结论；
- 关联的 Slice Integration、Infrastructure、Cross-Slice 或 E2E 证据（如适用）未被 Capability Acceptance 结果冒充替代。
