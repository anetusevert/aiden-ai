"""Add indexing status tracking to document_versions.

Revision ID: 20250124_000008
Revises: 20250124_000007
Create Date: 2025-01-24

This migration adds:
- is_indexed: boolean flag to track if embeddings are generated
- indexed_at: timestamp of last successful indexing
- embedding_model: model used for generating embeddings
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250124_000008"
down_revision: Union[str, None] = "20250124_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add indexing status columns to document_versions
    op.add_column(
        "document_versions",
        sa.Column("is_indexed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "document_versions",
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("embedding_model", sa.Text(), nullable=True),
    )

    # Add index for querying indexed versions
    op.create_index(
        op.f("ix_document_versions_is_indexed"),
        "document_versions",
        ["is_indexed"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_versions_is_indexed"),
        table_name="document_versions",
    )
    op.drop_column("document_versions", "embedding_model")
    op.drop_column("document_versions", "indexed_at")
    op.drop_column("document_versions", "is_indexed")
