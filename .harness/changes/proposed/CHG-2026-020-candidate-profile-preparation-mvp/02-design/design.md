# 设计说明

上传层先验证文件扩展名、声明 MIME、文件特征与大小，再由对象存储写入不透明对象。候选人资料准备 Repository 在一个事务内创建对象目录和业务资源；它只提交已校验的 `ResumeParseRequestV1`，由文档解析 Repository 在同一事务中持久化固定 `v1` 的解析任务。

候选人资料准备仅拥有简历、附加资料及其受控解析状态查询；它不读取、持久化或返回候选人画像。文档解析模块拥有 `candidate_profiles`、画像查询和解析终态：简历资源为 `processing` 时才允许后续 Worker 处理；解析成功必须同时写入 `candidate_profiles` 与终态。任何失败仅记录受控失败分类，禁止写入半成品画像。

候选人资料准备模块的验收边界止于上传资源、原子提交 `ResumeParseRequestV1` 和可靠投递至固定的文档解析任务；它不依赖 Worker、MinerU、Qwen 或画像成功。文档解析模块单独验收从已提交请求到 Worker、MinerU、Qwen、结构化校验和原子画像/终态的完整处理链路。
