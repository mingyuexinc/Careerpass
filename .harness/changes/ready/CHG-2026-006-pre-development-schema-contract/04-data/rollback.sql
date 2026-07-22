-- CHG-2026-006: Roll back only objects and constraints introduced by db-migrations.sql.

BEGIN;

ALTER TABLE IF EXISTS public.match_results
    ALTER COLUMN recall_score DROP NOT NULL,
    ALTER COLUMN skill_match_score DROP NOT NULL,
    ALTER COLUMN experience_match_score DROP NOT NULL,
    ALTER COLUMN salary_match_score DROP NOT NULL,
    ALTER COLUMN final_match_score DROP NOT NULL,
    ALTER COLUMN algorithm_version DROP NOT NULL,
    ALTER COLUMN recommendation_reason DROP NOT NULL;

ALTER TABLE IF EXISTS public.candidate_profiles
    ADD COLUMN IF NOT EXISTS candidate_id UUID;
UPDATE public.candidate_profiles AS profile
SET candidate_id = resume.candidate_id
FROM public.resumes AS resume
WHERE profile.resume_id = resume.id
  AND profile.candidate_id IS NULL;
ALTER TABLE public.candidate_profiles
    ALTER COLUMN candidate_id SET NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_candidate_profile_candidate'
          AND conrelid = 'public.candidate_profiles'::regclass
    ) THEN
        ALTER TABLE public.candidate_profiles
            ADD CONSTRAINT fk_candidate_profile_candidate
            FOREIGN KEY (candidate_id) REFERENCES public.candidates (id) ON DELETE CASCADE;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_candidate_profile_candidate
    ON public.candidate_profiles (candidate_id);
DROP INDEX IF EXISTS public.idx_candidate_profile_resume;

COMMIT;
