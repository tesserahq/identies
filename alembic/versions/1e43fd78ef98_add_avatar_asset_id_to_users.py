"""Add avatar_asset_id to users

Revision ID: 1e43fd78ef98
Revises: abc5c2f94c55
Create Date: 2025-07-14 17:41:59.214265

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1e43fd78ef98"
down_revision: Union[str, None] = "abc5c2f94c55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("avatar_asset_id", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "avatar_asset_id")
