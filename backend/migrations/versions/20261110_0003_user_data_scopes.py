"""Add user data-scope grants.

Revision ID: 20261110_0003
Revises: 20261110_0002
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0003"
down_revision: str | None = "20261110_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_data_scopes",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=20), nullable=False),
        sa.Column("scope_value", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE",
                                name=op.f("fk_user_data_scopes_user_id_users")),
        sa.CheckConstraint("scope_type IN ('global', 'company', 'department', 'owner')",
                           name=op.f("ck_user_data_scopes_type")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_data_scopes")),
        sa.UniqueConstraint("user_id", "scope_type", "scope_value",
                            name="uq_user_data_scopes_grant"),
    )
    op.create_index("ix_user_data_scopes_user_type", "user_data_scopes",
                    ["user_id", "scope_type"])


def downgrade() -> None:
    op.drop_index("ix_user_data_scopes_user_type", table_name="user_data_scopes")
    op.drop_table("user_data_scopes")
