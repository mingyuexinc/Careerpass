"""Allow S-03 semantic failures without legacy parse failure codes."""

from collections.abc import Sequence

from alembic import op

_CONSTRAINT_NAME = "ck_async_task_runs_ck_async_task_run_failure_code"

revision: str = "20260815_0008"
down_revision: str | None = "20260815_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The legacy constraint requires failure_code for every failed task. S-03
    # intentionally stores its public failure semantics in dedicated columns.
    op.execute(f'ALTER TABLE async_task_runs DROP CONSTRAINT "{_CONSTRAINT_NAME}"')
    condition = (
        "((status = 'failed' AND ("
        "(task_type::text = 'job_jd_parse' AND failure_code IS NULL AND failure_semantics IS NOT NULL) OR "
        "(task_type::text <> 'job_jd_parse' AND failure_code IS NOT NULL)"
        ")) OR "
        "(status <> 'failed' AND failure_code IS NULL AND failure_semantics IS NULL)"
        ")"
    )
    op.execute(
        f'ALTER TABLE async_task_runs ADD CONSTRAINT "{_CONSTRAINT_NAME}" CHECK {condition}',
    )


def downgrade() -> None:
    op.execute(f'ALTER TABLE async_task_runs DROP CONSTRAINT "{_CONSTRAINT_NAME}"')
    op.execute(
        f'ALTER TABLE async_task_runs ADD CONSTRAINT "{_CONSTRAINT_NAME}" CHECK ('
        "(status = 'failed' AND failure_code IS NOT NULL) OR "
        "(status <> 'failed' AND failure_code IS NULL)"
        ")",
    )
