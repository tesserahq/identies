"""Add soft delete to users

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-21 00:02:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    # A soft-deleted user must not block re-creating the same email or external id,
    # so uniqueness only applies to active rows.
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.create_index(
        "uq_users_email_active",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.drop_index("uq_users_external_id", table_name="users")
    op.create_index(
        "uq_users_external_id",
        "users",
        ["external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    # Note: restoring the plain unique constraints fails if a soft-deleted row and an
    # active row share an email or external_id. Resolve those before downgrading.
    op.drop_index("uq_users_external_id", table_name="users")
    op.create_index(
        "uq_users_external_id",
        "users",
        ["external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    op.drop_index("uq_users_email_active", table_name="users")
    op.create_unique_constraint("users_email_key", "users", ["email"])

    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_column("users", "deleted_at")
