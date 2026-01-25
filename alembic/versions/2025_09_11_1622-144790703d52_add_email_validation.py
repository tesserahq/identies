"""add email validation

Revision ID: 144790703d52
Revises: 35b0138f3b39
Create Date: 2025-09-11 16:22:11.400731

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "144790703d52"
down_revision: Union[str, None] = "35b0138f3b39"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # First, update all users with null email values using external_id + ".com" pattern
    connection = op.get_bind()

    # Update users with null emails using external_id + ".com" pattern
    connection.execute(
        text(
            "UPDATE users SET email = external_id || '.com' WHERE email IS NULL AND external_id IS NOT NULL"
        )
    )

    # Then make the email column non-nullable
    op.alter_column("users", "email", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # First make the email column nullable
    op.alter_column("users", "email", nullable=True)

    # Optionally, you could revert the email updates if needed
    # This would set emails back to NULL for users whose emails match the external_id + ".com" pattern
    # Uncomment the following lines if you want to revert the email updates:
    # connection = op.get_bind()
    # connection.execute(
    #     text("UPDATE users SET email = NULL WHERE email = external_id || '.com'")
    # )
