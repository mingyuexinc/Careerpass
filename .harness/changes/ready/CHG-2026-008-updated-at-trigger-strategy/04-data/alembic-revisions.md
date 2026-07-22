# Alembic Revision 映射

| 项目 | 内容 |
| --- | --- |
| Revision ID | 待实施时填写 |
| Down revision | 待实施时填写 |
| 执行入口 | `alembic upgrade <revision>` |
| 正向审阅 SQL | `db-migrations.sql` |
| 回滚审阅 SQL | `rollback.sql` |
| 前置条件 | `users` 与 `candidates` 表及其 `updated_at` 列存在。 |

不得手工绕过 Alembic 直接对生产 Schema 执行本目录 SQL。
