"""Add role memberships and HR business identities."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260811_0005"
down_revision: str | None = "20260727_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    role_enum = postgresql.ENUM("candidate", "hr", name="user_role_enum", create_type=False)
    role_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "hr_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_hr_profile_user", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_hr_profiles"),
        sa.UniqueConstraint("user_id", name="uq_hr_profile_user_id"),
    )
    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_user_roles"),
        sa.UniqueConstraint("user_id", "role", name="uq_user_role"),
    )
    op.execute(
        """
        CREATE TRIGGER trg_hr_profiles_set_updated_at
        BEFORE UPDATE ON hr_profiles
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_hr_profiles_set_updated_at ON hr_profiles")
    op.drop_table("user_roles")
    op.drop_table("hr_profiles")
    postgresql.ENUM("candidate", "hr", name="user_role_enum").drop(op.get_bind(), checkfirst=True)
