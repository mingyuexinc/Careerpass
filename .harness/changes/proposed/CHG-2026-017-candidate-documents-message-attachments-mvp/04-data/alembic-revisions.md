# Alembic 修订说明

当前变更包只提供评审用 SQL，不包含工程运行时 Alembic revision。

在候选人资料准备实现变更中，必须新增一条 Alembic revision，先创建内部对象目录 `stored_file_objects`，再创建原始附件表 `candidate_documents` 和引用型 `message_attachments` 及其外键、唯一约束和索引。内部对象目录应保存随机 `storage_key`、内容摘要、服务端检测 MIME、文件大小和内部状态，并以内容摘要唯一约束支持去重；`candidate_documents` 不得包含 `parse_data`、`parse_status` 或与 `AsyncTaskRun` 的关联，只能通过外键引用内部对象。降级时按依赖反向顺序移除对象。升级与降级逻辑以本目录 SQL 为审阅依据；运行时迁移的唯一入口是 `careerpass-backend/alembic/versions/` 下的 revision，禁止直接执行本目录 SQL。
