BEGIN;

ALTER TABLE IF EXISTS public.resumes
    ADD COLUMN IF NOT EXISTS upload_idempotency_key UUID NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_resume_candidate_upload_idempotency_key
    ON public.resumes (candidate_id, upload_idempotency_key)
    WHERE upload_idempotency_key IS NOT NULL;

ALTER TABLE IF EXISTS public.candidate_documents
    ADD COLUMN IF NOT EXISTS upload_idempotency_key UUID NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_document_candidate_upload_idempotency_key
    ON public.candidate_documents (candidate_id, upload_idempotency_key)
    WHERE upload_idempotency_key IS NOT NULL;

COMMIT;
