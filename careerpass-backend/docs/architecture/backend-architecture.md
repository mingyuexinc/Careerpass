# 后端总体架构

> 本文档描述当前后端代码的分层、依赖方向和基础设施边界，不定义业务范围、具体 Slice 契约或未来模块。

## 1. 当前运行结构

FastAPI 应用由 app/main.py 创建，app/api/router.py 汇总公开路由。运行时通过依赖注入组装 Service、Repository、数据库会话和基础设施适配器。

| 目录 | 职责 |
| --- | --- |
| app/api | HTTP 协议解析、身份依赖、统一响应和路由 |
| app/schemas | Pydantic 请求、响应和内部交接结构 |
| app/services | 用例编排、业务规则和事务协作 |
| app/repositories | 数据访问、归属查询和持久化操作 |
| app/infrastructure/database | SQLAlchemy Model、Session 和数据库运行时 |
| app/infrastructure/tasks | Celery、Dispatcher 和 Worker |
| app/infrastructure/storage | 本地对象存储与清理 |
| app/infrastructure/mineru_mcp*、qwen_profile.py | 受控外部能力适配器 |
| app/core | 配置、认证、安全、异常、日志和请求上下文 |

未在当前代码中出现的 agent、workflows、retrieval、memory 等目录不属于当前实现事实，仅在具体 Slice 证明需要后创建。

## 2. 依赖方向

主调用方向为：API → Service → Repository → Infrastructure。

- API 只处理协议、身份上下文和响应，不承载数据库操作。
- Service 编排用例和业务规则，不直接访问 ORM Session 或编写 SQL。
- Repository 是持久化访问和资源归属查询的唯一入口。
- Infrastructure 提供数据库、缓存、任务、文件和外部服务适配，不拥有业务规则。
- 模块不得依赖其他模块的 Repository 实现、ORM Model 或内部任务生命周期。

## 3. 身份与资源边界

当前身份由认证依赖解析为可信上下文。Resume、CandidateProfile、CandidateDocument 和异步解析任务的访问必须锚定当前 Candidate，不得仅凭资源 ID 读取或修改。

密码哈希、对象存储位置、令牌、原始简历、模型原始响应和内部异常不得跨出必要的 Repository 或 Infrastructure 边界。

## 4. 本地对象存储

当前对象存储是 Demo 范围内的本地适配器：

- 文件先写入临时位置，完成摘要、类型和大小校验后原子进入 ready；
- StoredFileObject 以内容摘要去重，内部 storage_key 不进入 API；
- 读取必须从已授权业务资源反查对象，不提供静态 URL；
- 清理只处理无业务引用对象，并保持失败可重试；
- 本设计不承诺云对象存储、通用文件中心或跨环境共享。

## 5. 架构变更

当前 Slice 引入新层级、反向依赖、共享状态拥有者或新的基础设施责任时，必须在 Slice Design 中裁决，并在 Readiness Check 前同步本文档。
