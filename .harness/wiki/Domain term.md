# 领域术语

## 核心术语

|  术语 |  英语  |  定义  |  代码中的体现  |
|- - - - |- - - - -| - - - - - -  - - -| 
|  求职者 | Candidate | 表示求职者主体，是系统中的用户实体 | `Candidate表` |
|  简历 | Resume | 仅指求职者用于岗位匹配、投递及生成求职者画像的正式求职简历；不承载证书、求职策略等附加材料。 | `Resume表` |
|  求职者资料 | Candidate Document | 求职者上传的非简历附加材料，用于补充求职背景或为 Agent 提供上下文。具体类型由 `document_type` 枚举限定，例如求职策略文档、证书及其他材料。 |  `Candidate Document表` |
| 求职者 Agent | Candidate Agent | 代表求职者执行沟通、检索资料、生成回复和推进求职流程的 AI Agent；不是用户本人。 | `candidate` 消息角色 |
| HR | HR | 岗位招聘方或其招聘代表，是求职沟通中的外部对话对象。当前可由模拟消息替代。 | `hr` 消息角色 |
|  求职者画像 | Candidate profile | 系统根据简历和用户输入生成的结构化候选人能力描述，用于岗位匹配和推荐 | `Candidate Profile表` |
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
