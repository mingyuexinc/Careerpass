-- 审阅用正向迁移脚本；运行时仅可通过工程内 Alembic revision 执行。
-- 前置条件：candidates、messages、document_type_enum 已存在。

DO $$
BEGIN
    CREATE TYPE stored_file_object_status_enum AS ENUM (
        'writing',
        'ready',
        'deleting'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS stored_file_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storage_key VARCHAR(512) NOT NULL UNIQUE,
    content_sha256 CHAR(64) NOT NULL UNIQUE,
    detected_mime_type VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL
        CHECK (file_size_bytes > 0 AND file_size_bytes <= 10000000),
    status stored_file_object_status_enum NOT NULL DEFAULT 'writing',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidate_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL,
    document_type document_type_enum NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    file_type VARCHAR NOT NULL,
    stored_file_object_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_candidate_document
        FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE,
    CONSTRAINT fk_candidate_document_stored_file_object
        FOREIGN KEY (stored_file_object_id) REFERENCES stored_file_objects (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_candidate_document_candidate
    ON candidate_documents (candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidate_document_stored_file_object
    ON candidate_documents (stored_file_object_id);

CREATE TABLE IF NOT EXISTS message_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL,
    candidate_document_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_attachment_message
        FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE,
    CONSTRAINT fk_attachment_candidate_document
        FOREIGN KEY (candidate_document_id) REFERENCES candidate_documents (id) ON DELETE RESTRICT,
    CONSTRAINT uq_attachment_message_document
        UNIQUE (message_id, candidate_document_id)
);

CREATE INDEX IF NOT EXISTS idx_attachment_message
    ON message_attachments (message_id);

CREATE INDEX IF NOT EXISTS idx_attachment_candidate_document
    ON message_attachments (candidate_document_id);
