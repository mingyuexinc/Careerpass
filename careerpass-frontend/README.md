# Careerpass 前端

Careerpass 前端是基于 TypeScript、React 和 Vite 构建的求职 Agent MVP。当前版本采用 Mock Repository 驱动，支持求职者和 HR 两种角色的完整业务流程，并为后续接入真实数据源保留清晰边界。

## 当前状态

- 前端 MVP 已完成。
- 正式运行代码位于 `src/`。
- HTML 原型、原型 Mock 数据和参考图片位于 `prototypes/`，不作为正式运行入口。
- 用户登录 Slice 已接入真实后端认证 API；除登录外，其余当前版本流程仍主要由 Mock Repository 驱动。
- S-06 求职目标和 S-DBG 调试恢复已接入真实后端 API；其他尚未联调的流程继续使用 Mock Repository。
- 当前数据只保存在浏览器内存中，刷新页面后恢复初始状态。

## 功能范围

### 求职者

- 角色登录和角色工作台
- 简历上传、解析中、解析成功和解析失败状态
- 其它求职资料上传
- 求职目标创建和启动条件展示
- 启动求职 Agent
- 查看投递轮次、岗位阶段和 Offer 达成进度
- Agent 达成目标 Offer 后自动结束

### HR

- 角色登录和 HR 工作台
- 岗位 JD 上传及逐文件结果状态展示
- 查看求职 Agent 沟通记录
- 发送消息并接收系统回复
- 更新单条投递记录的招聘阶段
- Offer 达标后同步求职者侧 Agent 状态

## 标准流程

1. 访问登录页，选择“求职者”或“HR”身份登录。
2. HR 进入“岗位 JD”，上传一份岗位文件。
3. 求职者上传简历，等待解析完成。
4. 求职者创建求职目标并启动 Agent。
5. 求职者在“求职进度”查看投递记录。
6. HR 在“求职沟通”发送消息，查看 Agent 回复。
7. HR 在“投递进度”逐步更新投递状态。
8. 任意投递记录达到 Offer 且满足目标数量后，Agent 自动结束。

应用刷新后会恢复初始工作区状态。

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

Vite 开发模式默认显示 S-DBG 调试恢复入口；如需在非开发模式的联调前端显示，设置未提交的环境变量 `VITE_DEBUG_RESET_ENABLED=true`。生产环境必须保持关闭。

## 前后端联调前置检查

前后端联调属于项目级基础服务基线的一部分。启动前确认后端 Docker Compose 已完成迁移，PostgreSQL、Redis、Backend、Worker 和 Dispatcher 正常，且 `http://localhost:8080/health/ready` 返回成功；再在前端目录运行 `npm run dev`，确认终端出现 `VITE ready` 和 `http://localhost:5173/`，保持该终端持续运行后再打开浏览器。

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
│   └── mock/fixtures/      # 本地 Fixture 和 Mock 实现
├── components/             # 页面头部和通用 UI 组件
├── domain/                 # 领域类型、状态值和状态映射
├── features/               # 业务 Hook 和功能模块
├── layouts/                # 公共布局和角色布局
├── pages/                  # 路由页面
├── stores/                 # 认证和工作区业务状态
├── styles/                 # 设计令牌和全局样式
└── test/                   # 单元、组件和页面测试
```

页面遵循以下数据访问方向，不直接读取 Fixture：

```text
页面 → 业务组件或 Hook → Repository → Mock Repository → 本地 Fixture
```

后续接入真实 API 时，优先替换 Repository 实现，不重写页面主要流程。

## 开发文档

- [前端标准流程与验收](docs/product/frontend-acceptance-flow.md)
- [前端正式产品形态与页面规格](docs/product/frontend-product-flow.md)
- [前端技术架构](docs/architecture/frontend-architecture.md)
- [前端开发决策](docs/decisions/frontend-development-decisions.md)
- [UI/UX 设计规范](docs/design/design-guidelines.md)
- [本地数据规范](docs/development/local-data-spec.md)
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
