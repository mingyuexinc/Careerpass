# 后端开发规范

> 本文档规定当前后端代码的实现约定，不定义产品范围、领域模型或单个 Slice 契约。

## 1. 分层实现

- Controller 负责请求解析、依赖注入和统一响应。
- Service 负责用例编排，不直接访问 ORM Session。
- Repository 负责查询、写入和资源归属条件。
- Infrastructure 适配数据库、Redis、Celery、对象存储和外部服务。
- 新代码不得绕过 Service/Repository 边界，也不得反向依赖上层。

## 2. 接口与数据结构（API 与 Schema）

- 公开路由使用 /api/v1 前缀；健康检查除外。
- 请求、响应和内部任务输入使用 Pydantic 结构校验，禁止传递任意字典代替已知契约。
- 所有业务响应使用 {code, msg, data}；不得使用 message 替代 msg。
- 具体路径、字段、状态和错误语义只在对应 Slice 的 `technical-design.md` 中定义。

## 3. 异常与错误码

- 业务错误使用集中定义的 ErrorCode 或等价受控枚举。
- 全局异常处理器负责 HTTP 状态、code、msg 和 data 的映射；业务代码不得自行拼装错误响应。
- msg 使用固定、脱敏场景文案，不拼接路径、堆栈、供应商原始错误或敏感原文。
- 未知异常对外返回 internal server error，对内日志只保留请求 ID、路径、异常类型和必要分类。

## 4. 数据与状态

- 所有用户资源查询必须包含当前用户或 Candidate 的归属条件。
- 状态更新必须校验前置状态和执行令牌；禁止直接覆盖状态字段绕过业务规则。
- 多资源一致性由 Service 协调事务、Repository 执行持久化。
- Schema 变化使用新的 Alembic revision，不修改已执行迁移。

## 5. 异步与外部能力

- 任务输入必须是固定版本的结构，不能包含文件路径、凭证、自由文本命令或模型参数。
- 外部调用设置超时、失败分类和适用的有限重试。
- LLM 输出经过 Pydantic 和业务规则校验后才可入库或驱动状态变化。
- Agent、Workflow 或模型不得生成 SQL、Shell 命令、工具名或未经校验的网络请求。

## 6. 测试

同一个交付目标的 Acceptance Test、Factory、Repository、Unit Test 和 Expected Manifest 必须放在 `tests/` 下同一个交付目标测试文件夹中；岗位 JD 等通用真实演示数据继续放在 `tests/fixtures/job_descriptions/`，不得移动；Expected Manifest 不得放在通用岗位数据目录中。运行生成的 `report.md` 和 `actual.json` 不属于测试源文件，统一输出到该交付目标测试文件夹下明确命名的结果目录，并作为开发者重点审阅对象。

- 核心业务规则、资源归属、状态迁移和幂等必须有单元测试。
- PostgreSQL、Redis、Celery、对象存储和外部服务的真实结论必须由相应集成证据支持。
- 测试替身只证明本地逻辑，不证明真实依赖可用。
- 内部能力 Slice 必须按 [`docs/integration/slice-acceptance-testing.md`](../../../docs/integration/slice-acceptance-testing.md) 明确区分 `Capability Acceptance`、`Slice Integration Test`、`Infrastructure Test`、`Cross-Slice Integration Test` 和 `E2E Test`；开发者核心能力自测不得自动扩大为完整工程链路验收。
- `Capability Acceptance` 使用固定 Fixture 直接验证真实核心业务输入到输出；需要数据库、任务、身份或文件对象的直接集成由 `Slice Integration Test` 单独验证。各层均不得预置被测 Slice 的最终输出。
- Redis、Celery、Dispatcher、Worker 等公共机制由 `Infrastructure Test` 验证；只有在专项测试声明时才纳入对应测试链路，并不得把其结果冒充核心能力自测结果。
- Fixture 只构造对应测试层所需的合法前置条件，必须经过受控 Factory、Repository 或正式用例并保留归属、状态机、唯一性和幂等约束。
- 测试命令必须是稳定的短命令入口，自动创建、清理临时数据并输出非零失败码；验收产物必须脱敏，不得包含凭证、未脱敏原文、完整内部路径或原始模型响应。
- 当前 pytest 配置要求整体覆盖率不低于 80%。
