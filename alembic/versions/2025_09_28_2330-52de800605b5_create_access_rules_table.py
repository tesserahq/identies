"""Create access rules table

Revision ID: 52de800605b5
Revises: de61d6c59952
Create Date: 2025-09-28 23:30:57.780212

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "52de800605b5"
down_revision: Union[str, None] = "de61d6c59952"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "access_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index(
            "uq_access_rules_kind_value", "kind", "value", "deleted_at", unique=True
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("access_rules")
