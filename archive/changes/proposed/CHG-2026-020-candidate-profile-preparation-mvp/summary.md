# 候选人资料准备 MVP

实现候选人正式简历与附加资料的受控上传和列表查询。G2 在简历资源事务中创建或复用 `ResumeParseRequestV1@v1` 对应的 queued `AsyncTaskRun`，返回受理中的 `processing` 状态；G3 负责后续解析、画像和终态。附加资料不进入该契约、不解析、不参与求职状态或下游准入，也不进入模型上下文。

数据库复用内部文件对象、简历、画像、候选人资料和异步任务运行模型；本次治理迁移不新增 handoff 表或运行时迁移。唯一跨包契约为 `.harness/contracts/resume-parse-request-v1.yaml`，联合门禁为 `JCG-2026-020-021-RESUME-PARSE-V1`；契约锁定和双方阶段 3 通过前不得恢复阶段 4/5。
