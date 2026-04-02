"""Migrate embeddings to native pgvector vector(384) type.

Revision ID: 20250124_000007
Revises: 20250124_000006
Create Date: 2025-01-24

This migration:
1. Adds a new column 'embedding_vec' of type vector(384)
2. Drops the old binary 'embedding' column
3. Renames 'embedding_vec' to 'embedding'

Note: This migration will lose any existing binary embeddings.
Run admin reindex after migration to regenerate embeddings.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250124_000007"
down_revision: Union[str, None] = "20250124_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop the old binary embedding column
    # Any existing embeddings will be lost - reindex required after migration
    op.drop_column("document_chunk_embeddings", "embedding")

    # Step 2: Add new native pgvector column (nullable initially for migration)
    # Using raw SQL because SQLAlchemy doesn't have native pgvector type support
    op.execute(
        "ALTER TABLE document_chunk_embeddings "
        "ADD COLUMN embedding vector(384)"
    )

    # Step 3: Set NOT NULL constraint (safe since we dropped and re-added, no existing rows need defaults)
    # If there were existing rows, they would need to be updated first
    op.execute(
        "ALTER TABLE document_chunk_embeddings "
        "ALTER COLUMN embedding SET NOT NULL"
    )


def downgrade() -> None:
    # Step 1: Drop the native vector column
    op.drop_column("document_chunk_embeddings", "embedding")

    # Step 2: Re-add the binary column
    op.add_column(
        "document_chunk_embeddings",
        sa.Column("embedding", sa.LargeBinary(), nullable=False, server_default=sa.text("'\\x00'")),
    )

    # Step 3: Remove the default
    op.execute(
        "ALTER TABLE document_chunk_embeddings "
        "ALTER COLUMN embedding DROP DEFAULT"
    )
