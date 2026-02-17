"""remove username column from users

Revision ID: 7d424edd689f
Revises: 9217c2891ec8
Create Date: 2026-02-18 00:21:26.646959

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7d424edd689f"
down_revision: Union[str, None] = "9217c2891ec8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("users", "username")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))
