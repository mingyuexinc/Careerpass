-- 仅回滚本次新增对象；按依赖反向顺序执行。

DROP TABLE IF EXISTS message_attachments;
DROP TABLE IF EXISTS candidate_documents;
DROP TABLE IF EXISTS stored_file_objects;
DROP TYPE IF EXISTS stored_file_object_status_enum;
