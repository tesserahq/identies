"""Add system accounts

Revision ID: 35b0138f3b39
Revises: 1e43fd78ef98
Create Date: 2025-08-01 10:21:14.097456

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "35b0138f3b39"
down_revision: Union[str, None] = "1e43fd78ef98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("service_account", sa.Boolean, default=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "service_account")
