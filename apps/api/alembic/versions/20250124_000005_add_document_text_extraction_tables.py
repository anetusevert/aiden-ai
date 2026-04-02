"""Add document text extraction tables (document_texts, document_chunks).

Revision ID: 20250124_000005
Revises: 20250124_000004
Create Date: 2025-01-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250124_000005"
down_revision: Union[str, None] = "20250124_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_texts table
    op.create_table(
        "document_texts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=False),
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
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_document_texts_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_document_texts_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_texts_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["document_versions.id"],
            name=op.f("fk_document_texts_version_id_document_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_texts")),
        sa.UniqueConstraint("version_id", name=op.f("uq_document_texts_version_id")),
    )
    op.create_index(
        op.f("ix_document_texts_tenant_id"),
        "document_texts",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_texts_workspace_id"),
        "document_texts",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_texts_document_id"),
        "document_texts",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_texts_version_id"),
        "document_texts",
        ["version_id"],
        unique=True,
    )

    # Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_document_chunks_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_document_chunks_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["document_versions.id"],
            name=op.f("fk_document_chunks_version_id_document_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint(
            "version_id", "chunk_index", name="uq_document_chunks_version_chunk_index"
        ),
    )
    op.create_index(
        op.f("ix_document_chunks_tenant_id"),
        "document_chunks",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunks_workspace_id"),
        "document_chunks",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunks_document_id"),
        "document_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunks_version_id"),
        "document_chunks",
        ["version_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop document_chunks table
    op.drop_index(
        op.f("ix_document_chunks_version_id"),
        table_name="document_chunks",
    )
    op.drop_index(
        op.f("ix_document_chunks_document_id"),
        table_name="document_chunks",
    )
    op.drop_index(
        op.f("ix_document_chunks_workspace_id"),
        table_name="document_chunks",
    )
    op.drop_index(
        op.f("ix_document_chunks_tenant_id"),
        table_name="document_chunks",
    )
    op.drop_table("document_chunks")

    # Drop document_texts table
    op.drop_index(
        op.f("ix_document_texts_version_id"),
        table_name="document_texts",
    )
    op.drop_index(
        op.f("ix_document_texts_document_id"),
        table_name="document_texts",
    )
    op.drop_index(
        op.f("ix_document_texts_workspace_id"),
        table_name="document_texts",
    )
    op.drop_index(
        op.f("ix_document_texts_tenant_id"),
        table_name="document_texts",
    )
    op.drop_table("document_texts")
