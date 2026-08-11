-- 前置条件：candidates.user_id 中不存在重复的非空值。
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_candidate_user_id'
          AND conrelid = 'candidates'::regclass
    ) THEN
        ALTER TABLE candidates
            ADD CONSTRAINT uq_candidate_user_id UNIQUE (user_id);
    END IF;
END
$$;
