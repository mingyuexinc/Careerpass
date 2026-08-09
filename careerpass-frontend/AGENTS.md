# Careerpass 前端项目入口规则

## 1. 项目定位

Careerpass 前端项目负责将已完成的 HTML 原型转化为基于 TypeScript + React 的正式前端 MVP。

当前目标是完成一个可维护、可重复验收、便于后续接入真实数据的前端应用，覆盖求职者和 HR 两种角色的核心求职 Agent 流程。

本项目当前以 Mock 数据驱动，不依赖当前后端文档和真实后端接口完成前端 MVP。

## 2. 当前开发阶段

当前处于正式前端工程准备阶段：

- 产品流程、页面形态和开发目标已经整理。
- 技术栈确定为 TypeScript + React。
- 技术架构、设计规范、本地数据和开发规范已经建立第一版。
- 正式前端源码尚未开始大规模实现。
- HTML 原型位于 `prototypes/`，只作为流程和视觉参考。

## 3. 技术基线

| 项目 | 约定 |
| --- | --- |
| 编程语言 | TypeScript |
| UI 框架 | React |
| 构建工具 | Vite |
| 路由 | React Router |
| 全局状态 | Zustand |
| 样式 | CSS Modules + 全局 CSS 变量 |
| 测试 | Vitest + Testing Library |
| 代码质量 | ESLint + Prettier |
| 数据源 | 当前使用 Mock Repository |

详细技术方案见 [`docs/architecture/frontend-architecture.md`](docs/architecture/frontend-architecture.md)。

## 4. 核心开发规则

### 4.1 正式源码和原型分离

- 正式前端源码只能放在 `src/`。
- `prototypes/` 保存 HTML 原型、原型 Mock 数据和参考图片。
- 可以复用原型中的流程、视觉方向和数据内容，但不得直接复制原型单文件业务逻辑作为正式实现。
- 正式前端不得直接依赖 `prototypes/html-reference/index.html` 的运行代码。

### 4.2 页面和数据分离

正式前端遵循：

```text
页面
→ 业务组件或 Hook
→ Repository 接口
→ Mock Repository
→ 本地 Fixture
```

- 页面不得直接读取或修改 Mock Fixture。
- 业务状态通过明确的 Action 变更。
- 状态值、显示文案、颜色和是否终态集中维护。
- 后续接入真实 API 时，优先替换数据访问实现，不重写页面流程。

### 4.3 组件和样式

- 优先复用已有通用组件。
- 页面组件负责组合页面，不复制大段 JSX 和 CSS。
- 业务组件放在对应的 `features/` 目录。
- 跨业务复用组件放在 `components/` 目录。
- 使用设计令牌管理颜色、字体、间距、圆角和阴影。
- 遵循浅灰背景、白色卡片、橙色品牌色和轻量阴影的视觉基准。

### 4.4 状态和交互

必须覆盖：

- 加载状态
- 空状态
- 失败状态
- 成功反馈
- 禁用状态
- 异步操作中的重复提交保护

关键约束：

- 简历解析成功前不能启动 Agent。
- 求职目标创建前不能启动 Agent。
- Agent 运行中不能替换当前轮次绑定的简历。
- Agent 结束后不能再次启动当前任务。
- HR 只能修改当前岗位下当前候选人的一条投递记录。
- 投递轮次为 0 时展示空状态，不展示虚构岗位。

### 4.5 敏感信息和错误信息

- 不在代码、Fixture、日志或页面中保存真实密码、Token、联系方式和完整简历原文。
- 不展示内部文件路径、原始异常堆栈或 Mock 内部结构。
- 错误使用简洁、面向用户的文案。
- 本地数据必须使用脱敏、虚构且可复现的内容。

## 5. 当前 MVP 范围

### 包含

- 求职者和 HR 角色登录。
- 求职者资料上传和简历解析状态展示。
- 求职目标创建和 Agent 启动。
- 首轮投递进度看板。
- HR 岗位 JD 上传。
- HR 求职沟通和系统 Agent 回复。
- HR 修改单条投递记录的求职进度。
- Offer 达标后 Agent 自动结束的页面表现。

### 不包含

- 真实账号体系和复杂注册。
- 真实后端接口联调。
- 真实文件存储和简历解析。
- 真实 Agent 调度、匹配和投递。
- 实时消息推送。
- 多轮投递、多目标和多份简历并行管理。
- 用户主动暂停或终止 Agent。
- 生产级监控、部署和高可用能力。

## 6. 文档导航

### 产品文档

| 文档 | 用途 |
| --- | --- |
| [`docs/product/frontend-acceptance-flow.md`](docs/product/frontend-acceptance-flow.md) | 标准业务流程、角色流程、产品规则和验收范围 |
| [`docs/product/frontend-product-flow.md`](docs/product/frontend-product-flow.md) | 正式前端产品形态、页面职责、页面规格和页面关系 |

### 决策和架构文档

| 文档 | 用途 |
| --- | --- |
| [`docs/decisions/frontend-development-decisions.md`](docs/decisions/frontend-development-decisions.md) | 开发目标、范围、重大决策和后续演进方向 |
| [`docs/architecture/frontend-architecture.md`](docs/architecture/frontend-architecture.md) | TypeScript + React 技术架构、目录、路由、状态和 Mock 方案 |

### 设计和开发文档

| 文档 | 用途 |
| --- | --- |
| [`docs/design/design-guidelines.md`](docs/design/design-guidelines.md) | 视觉风格、设计令牌、布局、组件和可访问性规范 |
| [`docs/development/local-data-spec.md`](docs/development/local-data-spec.md) | 本地数据、状态变化、场景数据集和恢复规则 |
| [`docs/development/frontend-guidelines.md`](docs/development/frontend-guidelines.md) | 文件组织、命名、组件、状态、测试和 AI/Codex 修改规范 |

## 7. 开发前阅读顺序

处理前端开发任务时，按任务需要阅读：

1. 先阅读本文件。
2. 涉及产品流程时阅读 `frontend-acceptance-flow.md`。
3. 涉及页面时阅读 `frontend-product-flow.md`。
4. 涉及数据时阅读 `local-data-spec.md`。
5. 涉及技术实现时阅读 `frontend-architecture.md`。
6. 涉及视觉时阅读 `design-guidelines.md`。
7. 编码前阅读 `frontend-guidelines.md`。

## 8. AI/Codex 工作规则

### 修改前

- 先确认任务属于正式前端 `src/` 还是原型 `prototypes/`。
- 阅读与任务相关的产品、架构、设计和数据文档。
- 优先查找并复用已有页面、组件、Hook、Store 和 Repository。
- 明确本次修改影响的页面、状态、Mock 数据和测试。

### 修改中

- 遵守 TypeScript 类型约束和目录边界。
- 不把固定业务数据直接写入页面组件。
- 不引入架构文档未确定的新框架或状态管理方式。
- 不擅自扩大 MVP 范围。
- 不修改与任务无关的用户代码。

### 修改后

- 执行与改动匹配的类型检查、Lint、测试或构建检查。
- 验证正常、加载、空、失败、成功和禁用状态。
- 验证关键业务流程没有被破坏。
- 如果改变页面范围、状态语义或技术方案，同步更新对应文档。

## 9. 当前推荐工作顺序

1. 初始化 Vite + React + TypeScript 工程。
2. 建立全局样式令牌和应用外壳。
3. 建立路由、角色布局和登录流程。
4. 建立领域类型、状态映射和本地 Fixture。
5. 建立 Repository 和 Mock 数据访问层。
6. 按求职者流程实现资料、任务和进度页面。
7. 按 HR 流程实现岗位、沟通和投递进度页面。
8. 补齐加载、空、失败、成功和禁用状态。
9. 完成关键流程测试和生产构建检查。
