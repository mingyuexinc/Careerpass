"""Store S-04 deterministic experience duration with its business unit."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260815_0010"
down_revision: str | None = "20260815_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_candidate_profile_years", "candidate_profiles", type_="check")
    op.alter_column(
        "candidate_profiles",
        "years_of_experience",
        existing_type=sa.Integer(),
        type_=sa.String(32),
        nullable=False,
        server_default=sa.text("'unknown'"),
        postgresql_using=(
            "CASE WHEN years_of_experience IS NULL THEN 'unknown' "
            "ELSE years_of_experience::text || '年' END"
        ),
    )
    op.create_check_constraint(
        "ck_candidate_profile_experience_duration",
        "candidate_profiles",
        "years_of_experience = 'unknown' OR "
        "years_of_experience ~ '^(0|[1-9][0-9]*)(个月|年)$'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_candidate_profile_experience_duration", "candidate_profiles", type_="check"
    )
    # PostgreSQL cannot cast the text default while changing the column type.
    # Remove it first, then restore the nullable integer shape below.
    op.alter_column(
        "candidate_profiles",
        "years_of_experience",
        existing_type=sa.String(32),
        server_default=None,
    )
    op.alter_column(
        "candidate_profiles",
        "years_of_experience",
        existing_type=sa.String(32),
        nullable=True,
    )
    op.alter_column(
        "candidate_profiles",
        "years_of_experience",
        existing_type=sa.String(32),
        type_=sa.Integer(),
        nullable=True,
        server_default=None,
        postgresql_using=(
            "CASE WHEN years_of_experience ~ '^[0-9]+年$' "
            "THEN replace(years_of_experience, '年', '')::integer ELSE NULL END"
        ),
    )
    op.create_check_constraint(
        "ck_candidate_profile_years",
        "candidate_profiles",
        "years_of_experience IS NULL OR years_of_experience >= 0",
    )
