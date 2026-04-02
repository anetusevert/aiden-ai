"""Add token_version to users table for session revocation.

Revision ID: 20250124_000009
Revises: 20250124_000008
Create Date: 2025-01-24

This migration adds token_version column to the users table.
Incrementing token_version invalidates all existing JWT tokens for that user.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250124_000009"
down_revision: Union[str, None] = "20250124_000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add token_version column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    """Remove token_version column from users table."""
    op.drop_column("users", "token_version")
