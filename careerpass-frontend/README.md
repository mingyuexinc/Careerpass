# Careerpass 前端

Careerpass 前端是基于 TypeScript、React 和 Vite 构建的求职 Agent MVP。当前版本采用 Mock Repository 驱动，支持求职者和 HR 两种角色的完整演示流程，便于重复演示和后续替换为真实数据源。

## 当前状态

- 前端 MVP 已完成。
- 正式运行代码位于 `src/`。
- HTML 原型、原型 Mock 数据和参考图片位于 `prototypes/`，不作为正式运行入口。
- 当前不依赖真实后端接口、真实认证或真实文件存储。
- Demo 数据只保存在浏览器内存中，刷新页面或重置 Demo 后恢复初始状态。

## 功能范围

### 求职者

- Demo 登录和角色工作台
- 简历上传、解析中、解析成功和解析失败状态
- 其它求职资料上传
- 求职目标创建和启动条件展示
- 启动求职 Agent
- 查看投递轮次、岗位阶段和 Offer 达成进度
- Agent 达成目标 Offer 后自动结束

### HR

- Demo 登录和 HR 工作台
- 岗位 JD 上传和岗位摘要展示
- 查看求职 Agent 沟通记录
- 发送消息并接收固定 Mock 回复
- 更新单条投递记录的招聘阶段
- Offer 达标后同步求职者侧 Agent 状态

## Demo 流程

1. 访问登录页，选择“求职者”或“HR”身份登录。
2. HR 进入“岗位 JD”，上传一份岗位文件。
3. 求职者上传简历，等待解析完成。
4. 求职者创建求职目标并启动 Agent。
5. 求职者在“求职进度”查看投递记录。
6. HR 在“求职沟通”发送消息，查看 Agent 回复。
7. HR 在“投递进度”逐步更新投递状态。
8. 任意投递记录达到 Offer 且满足目标数量后，Agent 自动结束。

侧边栏中的“重置演示数据”可以恢复初始 Demo 状态，便于重复演示。

## 技术栈

| 类别 | 技术 |
| --- | --- |
| 语言 | TypeScript |
| UI | React 19 |
| 构建 | Vite |
| 路由 | React Router |
| 状态 | Zustand |
| 样式 | CSS 设计令牌、响应式 CSS |
| 测试 | Vitest、Testing Library |
| 质量 | ESLint、Prettier |

## 环境要求

- Node.js 22.12 或更高版本
- npm 11 或更高版本

## 安装与运行

推荐在仓库根目录 `Careerpass/` 执行：

```bash
npm install
npm run frontend:install
npm run dev
```

也可以直接进入 `careerpass-frontend/` 目录执行：

```bash
npm install
npm run dev
```

开发服务器启动后，在浏览器访问终端输出的本地地址。

## 常用命令

```bash
npm run dev           # 启动开发服务器
npm run typecheck     # TypeScript 类型检查
npm run lint          # ESLint 检查
npm run format        # 使用 Prettier 格式化代码
npm run format:check  # 检查代码格式
npm run test:run      # 执行测试
npm run build         # 类型检查并构建生产版本
npm run preview       # 预览生产构建
```

当前已验证：类型检查、Lint、格式检查、7 项测试和生产构建均通过。

如果在仓库根目录执行前端质量检查，可以使用：

```bash
npm run frontend:check  # 类型、Lint 和格式检查
npm run frontend:test   # 执行前端测试
npm run frontend:build  # 构建前端生产版本
```

## 路由

| 路径 | 页面 | 角色 |
| --- | --- | --- |
| `/login` | 登录页 | 公共 |
| `/register` | 注册扩展说明页 | 公共 |
| `/candidate` | 求职者欢迎页 | 求职者 |
| `/candidate/documents` | 求职资料页 | 求职者 |
| `/candidate/job-goal` | 求职任务页 | 求职者 |
| `/candidate/progress` | 求职进度页 | 求职者 |
| `/hr` | HR 欢迎页 | HR |
| `/hr/jobs` | 岗位 JD 页 | HR |
| `/hr/conversations` | 求职沟通页 | HR |
| `/hr/applications` | 投递进度管理页 | HR |

## 目录结构

```text
src/
├── api/
│   ├── repositories/       # Repository 接口
│   └── mock/fixtures/      # Demo Fixture 和 Mock 实现
├── components/             # 页面头部和通用 UI 组件
├── domain/                 # 领域类型、状态值和状态映射
├── features/               # 业务 Hook 和功能模块
├── layouts/                # 公共布局和角色布局
├── pages/                  # 路由页面
├── stores/                 # 认证和 Demo 业务状态
├── styles/                 # 设计令牌和全局样式
└── test/                   # 单元、组件和页面测试
```

页面遵循以下数据访问方向，不直接读取 Fixture：

```text
页面 → 业务组件或 Hook → Repository → Mock Repository → Demo Fixture
```

后续接入真实 API 时，优先替换 Repository 实现，不重写页面主要流程。

## 开发文档

- [前端主演示流程](docs/product/frontend-demo-flow.md)
- [前端正式产品形态与页面规格](docs/product/frontend-product-flow.md)
- [前端技术架构](docs/architecture/frontend-architecture.md)
- [前端开发决策](docs/decisions/frontend-development-decisions.md)
- [UI/UX 设计规范](docs/design/design-guidelines.md)
- [Demo 数据规范](docs/development/demo-data.md)
- [前端开发规范](docs/development/frontend-guidelines.md)

## 当前非目标

本 MVP 不包含：

- 真实注册、登录和生产级权限体系
- 真实后端 API 联调
- 真实文件上传、对象存储和简历解析
- 真实 Agent 调度、岗位匹配和自动投递
- 实时消息推送
- 多轮投递、多目标和多份简历并行管理
- 用户主动暂停或终止 Agent
- 生产部署、监控和高可用能力
