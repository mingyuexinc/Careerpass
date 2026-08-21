# AI 编码指令

## 目录职责

.harness 只保存指导 AI 执行编码工作的规则和 Skill，不保存项目、产品或技术事实。

允许内容：

- AI 执行 Slice 开发的流程、门禁和回退规则；
- 可复用的 AI Coding Skill。

禁止内容：

- 产品范围、业务规则、领域模型、接口和数据库设计；
- 前后端架构、技术方案、环境说明和故障案例；
- 契约注册表、开发包和发布材料。

以上事实分别以根 AGENTS.md、前后端 AGENTS.md 及其 docs 目录为准。

## AI 阅读顺序

1. 阅读根 AGENTS.md、`docs/business/business-baseline.md` 和 `docs/business/business-fact-extraction.md`。
2. 阅读 `docs/integration/README.md`；涉及真实接入时读取对应 Integration Contract 和 Integration Scenario。
3. 阅读目标子工程 AGENTS.md，再按任务读取对应产品、架构、领域、数据和 Slice 事实源。
4. 读取 rules/AI coding workflow.md 确认当前 Slice Gate，并核对业务事实编号及其状态。
5. 需要建立或修订 Slice 开发文档时使用 `skills/slice-design/切片设计技能.md`。
6. 遇到实现细节是否需要人工确认的疑问时，使用 `skills/implementation-decision-autonomy/实现决策自主权.md`。

目录内指令不能替代代码、迁移或子工程事实源。
