"""Add embeddings and hybrid search support (pgvector + full-text).

Revision ID: 20250124_000006
Revises: 20250124_000005
Create Date: 2025-01-24

This migration:
1. Enables pgvector extension for vector similarity search
2. Adds tsvector column and GIN index on document_chunks for full-text search
3. Creates document_chunk_embeddings table for storing vector embeddings
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250124_000006"
down_revision: Union[str, None] = "20250124_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Step 2: Add tsvector column to document_chunks for full-text search
    # Using a generated column that auto-updates when text changes
    op.add_column(
        "document_chunks",
        sa.Column(
            "text_search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=True,
        ),
    )

    # Add GIN index on tsvector column for fast full-text search
    op.create_index(
        op.f("ix_document_chunks_text_search_vector"),
        "document_chunks",
        ["text_search_vector"],
        unique=False,
        postgresql_using="gin",
    )

    # Step 3: Create document_chunk_embeddings table
    op.create_table(
        "document_chunk_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=False), nullable=False),
        # vector(384) for embedding dimension - compatible with most models
        sa.Column("embedding", sa.LargeBinary(), nullable=False),  # We'll store as binary
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_document_chunk_embeddings_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_document_chunk_embeddings_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_chunk_embeddings_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["document_versions.id"],
            name=op.f("fk_document_chunk_embeddings_version_id_document_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            name=op.f("fk_document_chunk_embeddings_chunk_id_document_chunks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunk_embeddings")),
        sa.UniqueConstraint("chunk_id", name=op.f("uq_document_chunk_embeddings_chunk_id")),
    )

    # Create indexes for document_chunk_embeddings
    op.create_index(
        op.f("ix_document_chunk_embeddings_tenant_id"),
        "document_chunk_embeddings",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunk_embeddings_workspace_id"),
        "document_chunk_embeddings",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunk_embeddings_document_id"),
        "document_chunk_embeddings",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunk_embeddings_version_id"),
        "document_chunk_embeddings",
        ["version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunk_embeddings_chunk_id"),
        "document_chunk_embeddings",
        ["chunk_id"],
        unique=True,
    )
    # Composite index for tenant+workspace scoped queries
    op.create_index(
        "ix_document_chunk_embeddings_tenant_workspace",
        "document_chunk_embeddings",
        ["tenant_id", "workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop document_chunk_embeddings indexes and table
    op.drop_index(
        "ix_document_chunk_embeddings_tenant_workspace",
        table_name="document_chunk_embeddings",
    )
    op.drop_index(
        op.f("ix_document_chunk_embeddings_chunk_id"),
        table_name="document_chunk_embeddings",
    )
    op.drop_index(
        op.f("ix_document_chunk_embeddings_version_id"),
        table_name="document_chunk_embeddings",
    )
    op.drop_index(
        op.f("ix_document_chunk_embeddings_document_id"),
        table_name="document_chunk_embeddings",
    )
    op.drop_index(
        op.f("ix_document_chunk_embeddings_workspace_id"),
        table_name="document_chunk_embeddings",
    )
    op.drop_index(
        op.f("ix_document_chunk_embeddings_tenant_id"),
        table_name="document_chunk_embeddings",
    )
    op.drop_table("document_chunk_embeddings")

    # Drop tsvector column and index from document_chunks
    op.drop_index(
        op.f("ix_document_chunks_text_search_vector"),
        table_name="document_chunks",
    )
    op.drop_column("document_chunks", "text_search_vector")

    # Note: We don't drop pgvector extension as it might be used elsewhere
    # op.execute("DROP EXTENSION IF EXISTS vector")
