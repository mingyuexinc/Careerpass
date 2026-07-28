# Alembic revision

- Revision：`20260727_0003_candidate_preparation`
- Down revision：`20260725_0002_auth_user_candidate`
- 验收：隔离 PostgreSQL 已完成两次 `upgrade(head) → downgrade(20260725_0002) → upgrade(head)` 往返；表、触发器、约束和 Repository 认证链路通过验证。
# Dispatcher lease revision

- Revision: `20260727_0004_async_dispatch_leases`
- Down revision: `20260727_0003_candidate_preparation`
- Adds `dispatch_token`, `dispatch_lease_expires_at`, and `dispatched_at` to `async_task_runs`, plus the dispatch-lease lookup index.
- The fields protect only the Dispatcher publication/confirmation window. Worker result writes remain guarded by the existing `execution_token` and `execution_lease_expires_at`.
- Rollback removes only this index and these three nullable columns; it does not remove task-run history.
