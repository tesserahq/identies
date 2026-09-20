"""Add kind to users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-21 00:01:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add as nullable so existing rows can be backfilled, then enforce.
    op.add_column("users", sa.Column("kind", sa.String(length=20), nullable=True))
    op.execute(
        "UPDATE users SET kind = CASE WHEN service_account IS TRUE "
        "THEN 'service_account' ELSE 'human' END"
    )
    op.alter_column("users", "kind", nullable=False)
    op.create_check_constraint(
        "ck_users_kind", "users", "kind IN ('human', 'agent', 'service_account')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_kind", "users", type_="check")
    op.drop_column("users", "kind")
