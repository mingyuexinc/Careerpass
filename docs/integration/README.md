# 跨端联调与交付场景

## 1. 文档职责

本目录定义前端、后端和开发者共同使用的跨端交付事实：

- `Integration Contract`（跨端联调契约）：规定前端与后端交换的请求、响应、状态、错误和版本；
- `Integration Scenario`（集成交付场景）：规定开发者要演示的用户路径、演示数据、预期结果、自测结果和问题整改。

对于没有前端页面直接展示结果的内部能力 Slice，Integration Scenario 的交付目标可以是稳定内部入口、任务结果和 Acceptance Artifact；但场景必须先声明验证层。核心业务结果由 `Capability Acceptance` 验证，直接持久化由 `Slice Integration Test` 验证，Redis/Celery 等公共机制由 `Infrastructure Test` 验证，两个 Slice 的衔接由 `Cross-Slice Integration Test` 验证，完整用户流程由 `E2E Test` 验证。这不要求核心能力自测重复执行登录、上传等上游流程。统一测试边界、分层、自动断言和验收产物见 [`slice-acceptance-testing.md`](slice-acceptance-testing.md)。

本目录不替代以下事实源：

- 跨前后端业务语义以 [`../business/business-baseline.md`](../business/business-baseline.md) 为准；
- Slice 业务范围以对应 `slice-spec.md` 为准；
- Slice 技术实现和后端 Slice 间交接以对应 `technical-design.md` 为准；
- 页面、流程和视觉以前端 `docs/` 为准。

## 2. 三类边界

| 对象 | 负责回答的问题 |
| --- | --- |
| Slice | 开发什么业务能力 |
| Integration Contract | 前后端如何交换数据和状态 |
| Integration Scenario | 最终演示什么，如何证明交付完成 |

Slice 与 Integration Scenario 不要求一一对应：一个 Slice 可以支持多个场景，多个 Slice 也可以共同完成一个场景。

## 3. 交付状态

| 状态 | 含义 |
| --- | --- |
| `draft` | 场景或契约正在设计，不能作为开发依据 |
| `contract_locked` | 跨端契约已锁定，可以并行实现 |
| `backend_ready` | 后端实现和后端验证通过，尚未证明该交付场景已完成 |
| `integration_blocked` | 真实前端演示或内部能力验收存在阻断，必须记录问题并按规则回退 |
| `integration_delivered` | 对应场景的真实演示或稳定内部入口、自动断言、Acceptance Artifact、问题整改和回归验证均通过 |

`backend_ready` 不等于 `integration_delivered`。

## 4. 使用规则

1. Slice Select 时必须指定至少一个 Integration Scenario。
2. Slice Design 时必须建立或引用该场景的 Integration Contract。
3. 前端 Mock、HTTP 适配器和后端 API 都必须以同一份 Contract 为依据。
4. Mock 不得返回 Contract 未定义的后端事实；仅用于视觉占位的数据必须与真实 Contract 数据分开。
5. Readiness Check 必须准备场景所需的身份或自动构造方式、演示数据、环境和可执行步骤。
6. Verify 必须执行与场景类型和测试层匹配的真实交付路径：有前端展示结果的 Slice 执行真实前端演示；Internal Capability Slice 的开发者最小自测执行 Capability Acceptance，核对真实核心输出并生成 Acceptance Artifact。持久化、公共基础设施、跨 Slice 交接和完整用户流程分别由对应测试层验证。单元测试或脱离契约的 Mock 不能替代其声明的测试层。
7. 开发者填写“最小演示验证结果”；Coding Agent 根据其中的“其它问题”逐一填写“问题与整改”中“验收结果”之前的列，每个问题对应一条记录且数量保持一致；最右侧“验收结果”只能由开发者填写，未完成整改和开发者验收不得关闭场景。
8. 业务范围、权限、状态、契约、数据边界或跨 Slice 责任变化时，按影响回退对应 Gate。

## 5. 文件组织

```text
docs/integration/
├── README.md
├── integration-contract-template.md
├── integration-scenario-template.md
├── slice-acceptance-testing.md
└── slices/
    ├── slice-02-jd-upload/
        ├── integration-contract.md
        └── integration-scenario.md
    └── slice-03-jd-extraction/
        ├── integration-contract.md
        ├── integration-scenario.md
        └── fields.schema.json
```

使用 [`integration-contract-template.md`](integration-contract-template.md) 和 [`integration-scenario-template.md`](integration-scenario-template.md) 创建具体交付文档。
