-- CHG-2026-006: PostgreSQL 16.x. Execute through the Alembic revision for this change.
-- Preconditions: physical table names follow Data model.md.

BEGIN;

-- Candidate Profile ownership is derived exclusively from its source resume.
ALTER TABLE IF EXISTS public.candidate_profiles
    DROP CONSTRAINT IF EXISTS fk_candidate_profile_candidate;
DROP INDEX IF EXISTS public.idx_candidate_profile_candidate;
ALTER TABLE IF EXISTS public.candidate_profiles
    DROP COLUMN IF EXISTS candidate_id;
CREATE INDEX IF NOT EXISTS idx_candidate_profile_resume
    ON public.candidate_profiles (resume_id);

-- Refuse to convert incomplete historical results into apparently valid results.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM public.match_results
        WHERE recall_score IS NULL
           OR skill_match_score IS NULL
           OR experience_match_score IS NULL
           OR salary_match_score IS NULL
           OR final_match_score IS NULL
           OR algorithm_version IS NULL
           OR recommendation_reason IS NULL
    ) THEN
        RAISE EXCEPTION 'match_results contains incomplete rows; remediate before applying non-null contract';
    END IF;
END $$;

ALTER TABLE public.match_results
    ALTER COLUMN recall_score SET NOT NULL,
    ALTER COLUMN skill_match_score SET NOT NULL,
    ALTER COLUMN experience_match_score SET NOT NULL,
    ALTER COLUMN salary_match_score SET NOT NULL,
    ALTER COLUMN final_match_score SET NOT NULL,
    ALTER COLUMN algorithm_version SET NOT NULL,
    ALTER COLUMN recommendation_reason SET NOT NULL;

COMMIT;
