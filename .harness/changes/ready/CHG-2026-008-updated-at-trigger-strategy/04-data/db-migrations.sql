-- CHG-2026-008: Assumes the physical table names are users and candidates.
-- Run through Alembic (or an equivalent transactional migration runner).

DO $$
BEGIN
    IF to_regclass('public.users') IS NULL THEN
        RAISE EXCEPTION 'Required table public.users does not exist';
    END IF;

    IF to_regclass('public.candidates') IS NULL THEN
        RAISE EXCEPTION 'Required table public.candidates does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'updated_at'
    ) THEN
        RAISE EXCEPTION 'Required column public.users.updated_at does not exist';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'candidates'
          AND column_name = 'updated_at'
    ) THEN
        RAISE EXCEPTION 'Required column public.candidates.updated_at does not exist';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_set_updated_at ON public.users;
CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_candidates_set_updated_at ON public.candidates;
CREATE TRIGGER trg_candidates_set_updated_at
BEFORE UPDATE ON public.candidates
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();
