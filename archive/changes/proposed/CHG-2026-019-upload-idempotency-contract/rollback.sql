BEGIN;

DROP INDEX IF EXISTS public.uq_candidate_document_candidate_upload_idempotency_key;
ALTER TABLE IF EXISTS public.candidate_documents
    DROP COLUMN IF EXISTS upload_idempotency_key;

DROP INDEX IF EXISTS public.uq_resume_candidate_upload_idempotency_key;
ALTER TABLE IF EXISTS public.resumes
    DROP COLUMN IF EXISTS upload_idempotency_key;

COMMIT;
