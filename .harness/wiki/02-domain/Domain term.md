# 领域术语

## 认证与身份模块

| 术语 | 英语 | 定义 | 代码中的体现 |
| --- | --- | --- | --- |
| 用户 | User | 可通过认证进入系统的账号主体。MVP 注册时与唯一候选人原子创建。 | `users` |
| 求职者 | Candidate | 求职活动、简历、目标、匹配、投递与沟通资源的归属主体。 | `candidates` |
| 当前身份 | CurrentIdentity | 由 Access Token 与 Repository 复核得到的可信 `user_id`、`candidate_id` 上下文；客户端不得自行指定。 | `CurrentIdentity` |

## 候选人资料准备模块

| 术语 | 英语 | 定义 | 代码中的体现 |
| --- | --- | --- | --- |
| 简历 | Resume | 仅指用于画像、岗位匹配和投递的正式求职简历；不承载证书、求职策略等附加材料。 | `resumes` |
| 上传 | Upload | 候选人经受保护的 HTTP 上传接口提交简历或附加资料到系统的动作。该术语不用于岗位 JD 源文件进入系统。 | `POST /api/v1/resumes` 等 |
| 求职者资料 | Candidate Document | 求职者上传的非简历附加材料。可在候选人明确授权后作为系统内沟通附件引用；正文不自动进入 Agent/LLM 输入。 | `candidate_documents` |
| 内部文件对象 | Stored File Object | 由对象存储适配器管理的、以不透明键定位的候选人文件底层对象；不是通用文件中心。 | `stored_file_objects` |

## 简历解析模块

| 术语 | 英语 | 定义 | 代码中的体现 |
| --- | --- | --- | --- |
| 简历解析 | Resume Parsing | 对已授权正式简历进行受控异步提取、结构化校验和画像原子生成的处理链路。 | `ResumeParseRequest`、Celery Worker |
| 求职者画像 | Candidate Profile | 由已成功解析的正式简历确定性派生，并通过结构化与业务规则校验的候选人能力描述；是下游读取的简历结构化事实来源。 | `candidate_profiles` |
| 简历解析成功 | Resume Parsing Succeeded | 正式简历已完成提取、画像生成、Pydantic 与业务规则校验，并与画像在同一事务中持久化的终态。 | `resumes.parse_status = succeeded` |
| 简历解析失败 | Resume Parsing Failed | 正式简历未产生可消费完整结果的终态；失败原因仅以脱敏 `failure_code` 表达。 | `resumes.parse_status = failed`、`async_task_runs.failure_code` |
| 可用简历画像 | Usable Resume Profile | 归属当前候选人、对应简历解析成功且原子写入的画像。 | `resumes` → `candidate_profiles` |

## 岗位管理模块

| 术语 | 英语 | 定义 | 代码中的体现 |
| --- | --- | --- | --- |
| 岗位 | Job | 系统中的岗位实体；不等同于原始 JD 文件。 | `jobs` |
| 岗位 JD | Job Description | 岗位的原始描述及其通过第 5 步解析后得到的结构化字段；属于岗位聚合。 | `job_descriptions` |
| 岗位 JD 源文件 | Job Description Source File | 由开发者手工维护、供受控启动导入命令读取的 Markdown 文件；不是候选人上传文件。 | `.careerpass-job-jd/inbox/` |
| 导入 | Import | 受控启动导入命令从固定 JD 输入目录读取源文件并交给岗位 JD 处理链路的动作。该术语不表示候选人 HTTP 上传，也不等同于数据库持久化。 | 岗位 JD 启动导入命令 |
| 持久化 | Persistence | 将通过第 5 步结构化抽取和业务校验的岗位及 JD 业务事实写入数据库的动作。 | `jobs`、`job_descriptions` 的 Repository 事务 |
| 归档 | Archive | 在受控归档区保留原始 JD 源文件及其成功或失败处理结果的行为；不等同于删除数据库岗位，也不向候选人暴露文件名或路径。 | `.careerpass-job-jd/archive/` |
| 岗位 JD 解析 | Job Description Parsing | 对受控 Markdown JD 输入进行结构化抽取、结果 Schema 校验与失败处理的后续分支；技术路线由第 5 步裁定，不默认复用简历解析。 | 后续岗位 JD 解析分支 |
| 已解析岗位 JD 快照 | Parsed Job Description Snapshot | 已完成岗位 JD 解析并持久化、可供岗位匹配消费的结构化 JD 事实。 | `job_descriptions.parse_status = succeeded` |

## 求职目标模块

| 术语 | 英语 | 定义 | 代码中的体现 |
| --- | --- | --- | --- |
| 求职目标 | Job Goal | 候选人维护的目标岗位及基础筛选条件，状态受 `active / achieved / abandoned` 约束。 | `job_goals` |
| 活跃目标快照 | Active Goal Snapshot | 经归属与状态校验、可供下游匹配使用的当前活跃目标事实。 | `ActiveGoalSnapshot` |

## 岗位匹配模块

| 术语 | 英语 | 定义 | 代码中的体现 |
| --- | --- | --- | --- |
| 岗位匹配 | Job Matching | 基于已解析简历画像、已解析 JD 与活跃目标生成可解释结果的处理过程。 | `match_runs`、`match_results` |
| 匹配批次 | Match Run | 一次可追踪的岗位匹配执行。 | `match_runs` |
| 匹配结果 | Match Result | 评分、解释和算法版本完整的单个岗位匹配事实。 | `match_results` |
| 召回 | Recall | 从候选岗位集合中筛选候选项的检索阶段；仅在匹配模块实际启用时使用。 | R1 能力 |
| 重排序 | Rerank | 对候选岗位进一步排序的可选优化阶段。 | R2 能力 |

## 投递与进度模块

| 术语 | 英语 | 定义 | 代码中的体现 |
| --- | --- | --- | --- |
| 投递记录 | Application | 候选人对系统内岗位创建的一次投递事实；不代表真实外部投递。 | `applications` |
| 投递状态 | Application Status | 投递记录当前的合法业务状态。 | `applications.status` |
| 进度事件 | Progress Event | 投递状态变化产生的不可变审计事件。 | `progress_events` |

## AI 求职沟通模块

| 术语 | 英语 | 定义 | 代码中的体现 |
| --- | --- | --- | --- |
| 求职者 Agent | Candidate Agent | 代表候选人生成系统内沟通草稿或模拟回复的 AI 能力；不是候选人本人。 | `candidate` 消息角色 |
| HR | HR | 招聘方或其招聘代表；MVP 中由模拟消息或测试数据表示。 | `hr` 消息角色 |
| 沟通会话 | Conversation | 与一个系统内投递记录关联的会话上下文。 | `conversations` |
| 消息 | Message | 会话内由候选人、HR 或系统生成的一条沟通记录。 | `messages` |
