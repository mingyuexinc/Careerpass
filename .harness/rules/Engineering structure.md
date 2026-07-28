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
│   ├── orchestrator.py            # 结构化计划生成与调度协调
│   ├── state.py                   # 计划与运行状态定义
│   ├── router.py                  # 已注册业务任务路由
│   └── registry.py                # 代码注册的工作流清单与版本
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
|   Agent Orchestration Layer |  结构化计划、已注册工作流选择、策略校验后的调度；不直接执行业务写入     |
|  Workflow Layer |  执行固定输入输出的业务流程，协调 Service 与受控 AI 能力；记录运行状态     |
|   AI Capability Layer  |  LLM、结构化输出、Embedding、检索与重排序的受控能力封装     |
|   Repository Layer  |  数据访问、SQL映射     |
|   Infrastructure & Data Model Layer |  数据结构定义    |

**依赖方向**：API Layer → Application Service Layer → Agent Orchestration Layer → Workflow Layer → AI Capability Layer → Repository Layer → Infrastructure & Data Model Layer，禁止反向依赖

### Agent、工作流与检索职责边界

- `agent/` 只负责将意图或目标转为 Pydantic 计划、选择已注册工作流并提交调度；不得生成未注册流程或直接访问 ORM Session。
- `workflows/` 只执行代码定义的业务流程，调用 Service 实现业务规则和事务；不得自行编写 SQL、绕过状态机或以模型文本决定副作用。
- `services/` 是业务规则、授权复核和事务边界；对持久化访问仅依赖 Repository。
- `llm/` 负责模型调用、结构化输出和版本信息；输出必须在进入 Service 或 Workflow 前完成 Schema 校验。
- `retrieval/` 只暴露受控检索接口，负责过滤、召回、重排序和版本信息；不得直接暴露向量库客户端、ORM Session 或未校验外部请求给 Agent。
- 工作流注册表、计划 Schema 和任务运行记录仅在首次实际需要时创建在上述边界内，不得为未来需求预创建通用编排平台。



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

1. 数据库操作必须通过Repository，禁止在 Service、Agent、Workflow 或 Retriever 中写 SQL 或直接访问 ORM Session。
2. 新增文件必须按上述目录结构放置，禁止随意创建包/目录
3. Agent、Workflow、Retriever 不得生成或执行 Shell、未经校验的网络请求、未注册工具调用或模型拼接的 SQL。
