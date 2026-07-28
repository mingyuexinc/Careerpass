# 影响分析

- 认证后的候选人资源新增归属校验入口；所有查询均以可信 `candidate_id` 过滤。
- 本地对象存储仅接受服务端生成的不透明键，API 不返回路径、文件正文或解析原始错误。
- MinerU/Qwen 凭证仅作为解析 Worker 条件依赖；凭证真实可用性须由外部集成全链路证明。
- 关联 CHG-017、CHG-018 与 CHG-019 的附件、画像和上传幂等契约。
- 子任务 8 将原先位于候选人资料准备模块的画像查询、终态持久化及解析任务创建迁移至文档解析模块；资料模块只通过 `ResumeParseRequestV1` 提交受控请求，不依赖文档解析的 ORM、Repository、任务状态或 Worker 实现。
- 保持 `GET /api/v1/resumes/{resume_id}/profile` 的外部 URL，处理器和 Service 归属迁移为文档解析模块，避免破坏既有调用方。
