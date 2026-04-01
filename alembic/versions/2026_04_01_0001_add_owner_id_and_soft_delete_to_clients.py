"""Add owner_id and soft delete to clients

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-01 00:01:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column(
            "owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
    )
    op.create_index("idx_clients_owner_id", "clients", ["owner_id"])


def downgrade() -> None:
    op.drop_index("idx_clients_owner_id", table_name="clients")
    op.drop_column("clients", "owner_id")
