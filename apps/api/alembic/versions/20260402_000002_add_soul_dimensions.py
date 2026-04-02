"""Add soul_dimensions and interaction_count to user_twins.

Revision ID: 20260402_000002
Revises: 20260402_000001
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260402_000002"
down_revision = "20260402_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_twins",
        sa.Column("soul_dimensions", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "user_twins",
        sa.Column("interaction_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("user_twins", "interaction_count")
    op.drop_column("user_twins", "soul_dimensions")
