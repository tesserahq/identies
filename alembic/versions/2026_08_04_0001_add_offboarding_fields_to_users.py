"""Add offboarding and soft delete fields to users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-04 00:01:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    op.add_column(
        "users", sa.Column("offboarding_scheduled_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "offboarding_scheduled_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_users_offboarding_scheduled_at", "users", ["offboarding_scheduled_at"]
    )

    op.add_column(
        "users", sa.Column("deleted_event_published_at", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "deleted_event_published_at")

    op.drop_index("idx_users_offboarding_scheduled_at", table_name="users")
    op.drop_column("users", "offboarding_scheduled_by")
    op.drop_column("users", "offboarding_scheduled_at")

    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_column("users", "deleted_at")
