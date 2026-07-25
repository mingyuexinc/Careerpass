DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_candidate_user_id'
          AND conrelid = 'candidates'::regclass
    ) THEN
        ALTER TABLE candidates
            DROP CONSTRAINT uq_candidate_user_id;
    END IF;
END
$$;
