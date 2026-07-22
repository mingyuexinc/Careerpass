# 工程结构规范

## 前后端分离Agent项目目录结构

### 前端

### FastAPI 后端 （`Careerpass-backend`）

```
app/
├── main.py                        # FastAPI 应用入口
├── api/                           # 接口层
│   └── v1/
├── schemas/                       # API 输入输出模型
├── agent/                         # Agent 核心层
│   ├── orchestrator.py            # Agent 流程编排
│   ├── state.py                   # Agent 全局状态定义
│   └── router.py                  # 业务任务路由
├── workflows/                     # 业务工作流层
│   ├── job_matching/
│   ├── communication/
│   └── application_tracking/
├── llm/                           # 大模型基础能力封装
│   ├── client.py                  # 统一LLM调用接口
│   ├── embedding.py               # Embedding模型封装
│   └── structured_output.py       # 结构化输出解析
├── prompts/                       # Prompt统一管理
├── tools/                         # Agent可调用工具
├── retrieval/                     # RAG检索能力
│   ├── retrievers/
│   └── rerankers/
├── memory/                        # Agent记忆管理
├── services/                      # 应用服务层
├── repositories/                  # 数据访问抽象
├── infrastructure/                # 基础设施实现
│   ├── database/
│   ├── cache/
│   └── vector_store/
├── core/                          # 全局基础配置
└── utils/
```

## 七层架构

```
API Layer → Application Service Layer → Agent Orchestration Layer → Workflow Layer → AI Capability Layer → Repository Layer → Infrastructure & Data Model Layer
```

|   Layer   |   Responsibility   |
| - - - - - -| - - - - - - - - - - - |
|   API Layer | 请求路由、参数校验、响应构造     |
|   Application Service Layer |  业务逻辑、事务管理     |
|   Agent Orchestration Layer |  意图识别、任务规划     |
|  Workflow Layer |  任务拆解、工具调用     |
|   AI Capability Layer  |  能力封装、暴露接口     |
|   Repository Layer  |  数据访问、SQL映射     |
|   Infrastructure & Data Model Layer |  数据结构定义    |

**依赖方向**：API Layer → Application Service Layer → Agent Orchestration Layer → Workflow Layer → AI Capability Layer → Repository Layer → Infrastructure & Data Model Layer，禁止反向依赖



## 模块边界

|   Module   |   Depends On  |  Description  |
| - -  -- - - -| - - - - - - - - - - | - - - - - - - - - |
|  求职目标管理模块 |  无    |  管理求职目标  |
|  求职者资料管理模块 |  无  |  管理用户上传的资料 |
|  文档处理模块 |  无  |  对用户上传的资料进行相应处理（录入、解析、结构化） |
|  岗位管理模块 |  无  |  管理岗位原始JD及结构化岗位信息 |
|  **岗位匹配模块** |  求职者资料管理模块、岗位管理模块  | 负责针对求职者简历给出岗位推荐 |
|  **投递管理模块**|  岗位匹配模块、岗位管理模块、求职者资料管理模块   | 将推荐岗位转化为投递记录 |
|   **AI 求职沟通模块**  |  投递管理模块、求职者资料管理模块、求职目标管理模块   | 负责HR沟通的自动回复 |
|  求职进度管理模块 |  投递管理模块   |  管理岗位的求职状态变化  |





## 红线规则

1. 数据库操作必须通过Repository，禁止在Service 中写 SQL
2. 新增文件必须按上述目录结构放置，禁止随意创建包/目录

