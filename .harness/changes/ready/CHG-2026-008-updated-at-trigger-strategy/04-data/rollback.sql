-- CHG-2026-008: Roll back only the database objects introduced by db-migrations.sql.

DROP TRIGGER IF EXISTS trg_candidates_set_updated_at ON public.candidates;
DROP TRIGGER IF EXISTS trg_users_set_updated_at ON public.users;
DROP FUNCTION IF EXISTS public.set_updated_at();
