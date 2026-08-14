# 跨端联调与交付场景

## 1. 文档职责

本目录定义前端、后端和开发者共同使用的跨端交付事实：

- `Integration Contract`（跨端联调契约）：规定前端与后端交换的请求、响应、状态、错误和版本；
- `Integration Scenario`（集成交付场景）：规定开发者要演示的用户路径、演示数据、预期结果、自测结果和问题整改。

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
| `backend_ready` | 后端实现和后端验证通过，尚未证明真实前端可交付 |
| `integration_blocked` | 真实前端演示存在阻断，必须记录问题并按规则回退 |
| `integration_delivered` | 演示场景、自测、问题整改和回归验证均通过 |

`backend_ready` 不等于 `integration_delivered`。

## 4. 使用规则

1. Slice Select 时必须指定至少一个 Integration Scenario。
2. Slice Design 时必须建立或引用该场景的 Integration Contract。
3. 前端 Mock、HTTP 适配器和后端 API 都必须以同一份 Contract 为依据。
4. Mock 不得返回 Contract 未定义的后端事实；仅用于视觉占位的数据必须与真实 Contract 数据分开。
5. Readiness Check 必须准备演示账号、演示数据、环境和可执行步骤。
6. Verify 必须执行真实前端演示路径，并记录实际结果；单元测试或接口测试不能替代场景验收。
7. 开发者填写“最小演示验证结果”；Coding Agent 根据其中的“其它问题”逐一填写“问题与整改”中“验收结果”之前的列，每个问题对应一条记录且数量保持一致；最右侧“验收结果”只能由开发者填写，未完成整改和开发者验收不得关闭场景。
8. 业务范围、权限、状态、契约、数据边界或跨 Slice 责任变化时，按影响回退对应 Gate。

## 5. 文件组织

```text
docs/integration/
├── README.md
├── integration-contract-template.md
├── integration-scenario-template.md
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
