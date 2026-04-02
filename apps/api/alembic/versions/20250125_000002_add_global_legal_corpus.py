"""Add Global Legal Corpus tables and is_platform_admin to users.

Revision ID: 20250125_000002
Revises: 20250125_000001
Create Date: 2025-01-25

This migration adds:
1. is_platform_admin column to users table
2. legal_instruments table for storing law/regulation metadata
3. legal_instrument_versions table for file versions
4. legal_texts table for extracted text
5. legal_chunks table for text chunks
6. legal_chunk_embeddings table for vector embeddings

The global legal corpus is separate from tenant/workspace documents
and can only be managed by platform administrators.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250125_000002"
down_revision: Union[str, None] = "20250125_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add is_platform_admin column to users table
    op.add_column(
        "users",
        sa.Column(
            "is_platform_admin",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_users_is_platform_admin"),
        "users",
        ["is_platform_admin"],
        unique=False,
    )

    # Step 2: Create legal_instruments table
    op.create_table(
        "legal_instruments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "jurisdiction",
            sa.String(32),
            nullable=False,
        ),
        sa.Column(
            "instrument_type",
            sa.String(64),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("title_ar", sa.Text(), nullable=True),
        sa.Column("official_source_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("effective_at", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_legal_instruments_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_instruments")),
    )
    op.create_index(
        op.f("ix_legal_instruments_jurisdiction"),
        "legal_instruments",
        ["jurisdiction"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_instruments_instrument_type"),
        "legal_instruments",
        ["instrument_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_instruments_status"),
        "legal_instruments",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_instruments_created_at"),
        "legal_instruments",
        ["created_at"],
        unique=False,
    )

    # Step 3: Create legal_instrument_versions table
    op.create_table(
        "legal_instrument_versions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("legal_instrument_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version_label", sa.String(64), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_provider", sa.String(32), nullable=False),
        sa.Column("storage_bucket", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("extracted_text_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "is_indexed",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(
            ["legal_instrument_id"],
            ["legal_instruments.id"],
            name=op.f("fk_legal_instrument_versions_legal_instrument_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_legal_instrument_versions_uploaded_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_instrument_versions")),
    )
    op.create_index(
        op.f("ix_legal_instrument_versions_legal_instrument_id"),
        "legal_instrument_versions",
        ["legal_instrument_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_instrument_versions_is_indexed"),
        "legal_instrument_versions",
        ["is_indexed"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_instrument_versions_language"),
        "legal_instrument_versions",
        ["language"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_instrument_versions_created_at"),
        "legal_instrument_versions",
        ["created_at"],
        unique=False,
    )

    # Step 4: Create legal_texts table
    op.create_table(
        "legal_texts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.Text(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["legal_instrument_versions.id"],
            name=op.f("fk_legal_texts_version_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_texts")),
    )
    op.create_index(
        op.f("ix_legal_texts_version_id"),
        "legal_texts",
        ["version_id"],
        unique=True,
    )

    # Step 5: Create legal_chunks table
    op.create_table(
        "legal_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column(
            "text_search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["legal_instruments.id"],
            name=op.f("fk_legal_chunks_instrument_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["legal_instrument_versions.id"],
            name=op.f("fk_legal_chunks_version_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_chunks")),
        sa.UniqueConstraint(
            "version_id", "chunk_index", name="uq_legal_chunks_version_chunk_index"
        ),
    )
    op.create_index(
        op.f("ix_legal_chunks_instrument_id"),
        "legal_chunks",
        ["instrument_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_chunks_version_id"),
        "legal_chunks",
        ["version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_chunks_text_search_vector"),
        "legal_chunks",
        ["text_search_vector"],
        unique=False,
        postgresql_using="gin",
    )

    # Step 6: Create legal_chunk_embeddings table
    op.create_table(
        "legal_chunk_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=False), nullable=False),
        # Using pgvector's native vector(384) type
        sa.Column("embedding", sa.Text(), nullable=False),  # Will be cast to vector
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["legal_instruments.id"],
            name=op.f("fk_legal_chunk_embeddings_instrument_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["legal_instrument_versions.id"],
            name=op.f("fk_legal_chunk_embeddings_version_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["legal_chunks.id"],
            name=op.f("fk_legal_chunk_embeddings_chunk_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_chunk_embeddings")),
        sa.UniqueConstraint("chunk_id", name="uq_legal_chunk_embeddings_chunk_id"),
    )
    op.create_index(
        op.f("ix_legal_chunk_embeddings_instrument_id"),
        "legal_chunk_embeddings",
        ["instrument_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_chunk_embeddings_version_id"),
        "legal_chunk_embeddings",
        ["version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_legal_chunk_embeddings_chunk_id"),
        "legal_chunk_embeddings",
        ["chunk_id"],
        unique=True,
    )

    # Alter the embedding column to use pgvector type
    op.execute(
        "ALTER TABLE legal_chunk_embeddings "
        "ALTER COLUMN embedding TYPE vector(384) "
        "USING embedding::vector(384)"
    )


def downgrade() -> None:
    # Drop legal_chunk_embeddings
    op.drop_index(
        op.f("ix_legal_chunk_embeddings_chunk_id"),
        table_name="legal_chunk_embeddings",
    )
    op.drop_index(
        op.f("ix_legal_chunk_embeddings_version_id"),
        table_name="legal_chunk_embeddings",
    )
    op.drop_index(
        op.f("ix_legal_chunk_embeddings_instrument_id"),
        table_name="legal_chunk_embeddings",
    )
    op.drop_table("legal_chunk_embeddings")

    # Drop legal_chunks
    op.drop_index(
        op.f("ix_legal_chunks_text_search_vector"),
        table_name="legal_chunks",
    )
    op.drop_index(
        op.f("ix_legal_chunks_version_id"),
        table_name="legal_chunks",
    )
    op.drop_index(
        op.f("ix_legal_chunks_instrument_id"),
        table_name="legal_chunks",
    )
    op.drop_table("legal_chunks")

    # Drop legal_texts
    op.drop_index(
        op.f("ix_legal_texts_version_id"),
        table_name="legal_texts",
    )
    op.drop_table("legal_texts")

    # Drop legal_instrument_versions
    op.drop_index(
        op.f("ix_legal_instrument_versions_created_at"),
        table_name="legal_instrument_versions",
    )
    op.drop_index(
        op.f("ix_legal_instrument_versions_language"),
        table_name="legal_instrument_versions",
    )
    op.drop_index(
        op.f("ix_legal_instrument_versions_is_indexed"),
        table_name="legal_instrument_versions",
    )
    op.drop_index(
        op.f("ix_legal_instrument_versions_legal_instrument_id"),
        table_name="legal_instrument_versions",
    )
    op.drop_table("legal_instrument_versions")

    # Drop legal_instruments
    op.drop_index(
        op.f("ix_legal_instruments_created_at"),
        table_name="legal_instruments",
    )
    op.drop_index(
        op.f("ix_legal_instruments_status"),
        table_name="legal_instruments",
    )
    op.drop_index(
        op.f("ix_legal_instruments_instrument_type"),
        table_name="legal_instruments",
    )
    op.drop_index(
        op.f("ix_legal_instruments_jurisdiction"),
        table_name="legal_instruments",
    )
    op.drop_table("legal_instruments")

    # Drop is_platform_admin from users
    op.drop_index(op.f("ix_users_is_platform_admin"), table_name="users")
    op.drop_column("users", "is_platform_admin")
