# 领域术语

## 核心术语

|  术语 |  英语  |  定义  |  代码中的体现  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  求职者 | Candidate | 表示求职者主体，是系统中的用户实体 | `Candidate表` |
|  简历 | Resume | 仅指求职者用于岗位匹配、投递及生成求职者画像的正式求职简历；不承载证书、求职策略等附加材料。 | `Resume表` |
|  求职者资料 | Candidate Document | 求职者上传的非简历附加材料，用于补充求职背景或为 Agent 提供上下文。具体类型由 `document_type` 枚举限定，例如求职策略文档、证书及其他材料。 |  `Candidate Document表` |
| 求职者 Agent | Candidate Agent | 代表求职者执行沟通、检索资料、生成回复和推进求职流程的 AI Agent；不是用户本人。 | `candidate` 消息角色 |
| HR | HR | 岗位招聘方或其招聘代表，是求职沟通中的外部对话对象。当前可由模拟消息替代。 | `hr` 消息角色 |
|  求职者画像 | Candidate profile | 由已成功解析的正式简历确定性派生、并通过结构化与业务规则校验的候选人能力描述；是岗位匹配、投递和 AI 沟通读取的简历结构化事实来源，不包含系统推荐或推断的目标职位。 | `Candidate Profile表` |
| 简历解析成功 | Resume parsing succeeded | 正式简历已完成文本提取、结构化画像生成、Pydantic 与业务规则校验，并与对应画像在同一事务中原子持久化的终态。`parse_status = succeeded` 已包含“画像成功”，不另设独立画像成功状态。 | `resumes.parse_status = succeeded`，且存在对应 `Candidate Profile` |
| 简历解析失败 | Resume parsing failed | 正式简历未能产生可消费完整结果的终态。文本提取失败、结构化画像生成或校验失败、画像原子写入失败等，均按解析失败处理；不另设独立“画像失败”状态。终态原因仅以脱敏 `failure_code` 表达。 | `resumes.parse_status = failed`、`AsyncTaskRun.failure_code` |
| 可用简历画像 | Usable resume profile | 来源归属当前候选人、`parse_status = succeeded`，且由该简历解析成功时原子写入的画像。下游模块可在自身操作中结合具体业务规则使用，不构成统一求职状态。 | `resumes` → `Candidate Profile` |
|  岗位 | Job | 表示一个岗位实体，不包含完整岗位描述文本 | `Job表` |
|  岗位文本描述 | Job Description | 是岗位的文本描述，通过解析得到结构化岗位要求 | `Job Description表` |
|  岗位画像 | Job Profile | 从 JD 中抽取出的结构化岗位需求，用于和 Candidate Profile 匹配 | `xxxx` |

## 技术术语

|  术语 | 说明  |
|- - - - |- - - - -|
|  Job Matching | 指候选人与岗位之间的匹配配度计算过程 |
|  Recall | 从大量岗位中快速筛选候选集合的阶段 |
|  Rerank | 对召回结果进行精细排序的阶段 |
|  Match Result | 表示一次候选人与岗位匹配计算的结果 |


## 岗位申请

|  术语 | 说明  |
|- - - - |- - - - -|
|  Job Matching | 指候选人与岗位之间的匹配配度计算过程 |
|  Recall | 从大量岗位中快速筛选候选集合的阶段 |
|  Rerank | 对召回结果进行精细排序的阶段 |
|  Match Result | 表示一次候选人与岗位匹配计算的结果 |

## 业务流程状态术语

|  术语 | 说明  |
|- - - - |- - - - -|
|  Application | 表示候选人针对某个岗位产生的一次求职行为 |
|  Application Status | 表示当前的投递状态 |
|  Progress Event | 是记录岗位申请状态变化的不可变事件 |
