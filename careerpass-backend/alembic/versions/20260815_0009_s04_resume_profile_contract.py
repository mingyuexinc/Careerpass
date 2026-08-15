"""Add S-04 resume profile business fields and content uniqueness."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260815_0009"
down_revision: str | None = "20260815_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("full_name", sa.String(128), nullable=True))
    op.add_column("candidate_profiles", sa.Column("phone", sa.String(64), nullable=True))
    op.add_column("candidate_profiles", sa.Column("email", sa.String(254), nullable=True))
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "matching_readiness",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'matching_not_ready'"),
        ),
    )
    op.drop_constraint("ck_candidate_profile_target_titles", "candidate_profiles", type_="check")
    op.create_check_constraint(
        "ck_candidate_profile_matching_readiness",
        "candidate_profiles",
        "matching_readiness IN ('matching_ready', 'matching_not_ready')",
    )
    op.create_index(
        "uq_resume_candidate_stored_file",
        "resumes",
        ["candidate_id", "stored_file_object_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_resume_candidate_stored_file", table_name="resumes")
    op.drop_constraint(
        "ck_candidate_profile_matching_readiness", "candidate_profiles", type_="check"
    )
    op.create_check_constraint(
        "ck_candidate_profile_target_titles",
        "candidate_profiles",
        "cardinality(target_job_titles) >= 1",
    )
    op.drop_column("candidate_profiles", "matching_readiness")
    op.drop_column("candidate_profiles", "email")
    op.drop_column("candidate_profiles", "phone")
    op.drop_column("candidate_profiles", "full_name")
