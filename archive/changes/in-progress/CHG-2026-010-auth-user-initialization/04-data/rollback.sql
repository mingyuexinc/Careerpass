-- 审阅用回滚摘要；实际执行入口为对应 Alembic revision 的 downgrade。
DROP TRIGGER IF EXISTS trg_candidates_set_updated_at ON candidates;
DROP TRIGGER IF EXISTS trg_users_set_updated_at ON users;
DROP TABLE IF EXISTS candidates;
DROP TABLE IF EXISTS users;
DROP FUNCTION IF EXISTS set_updated_at();
