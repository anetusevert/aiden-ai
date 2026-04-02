"""Add document vault tables (documents, document_versions).

Revision ID: 20250124_000004
Revises: 20250124_000003
Create Date: 2025-01-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250124_000004"
down_revision: Union[str, None] = "20250124_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("jurisdiction", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("confidentiality", sa.String(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_documents_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_documents_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_documents_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(
        op.f("ix_documents_tenant_id"),
        "documents",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_documents_workspace_id"),
        "documents",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_documents_created_by_user_id"),
        "documents",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_documents_tenant_workspace_created_at"),
        "documents",
        ["tenant_id", "workspace_id", "created_at"],
        unique=False,
    )

    # Create document_versions table
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_provider", sa.String(), nullable=False),
        sa.Column("storage_bucket", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_document_versions_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_document_versions_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_versions_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_document_versions_uploaded_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_versions")),
        sa.UniqueConstraint(
            "document_id", "version_number", name="uq_document_versions_document_version"
        ),
    )
    op.create_index(
        op.f("ix_document_versions_tenant_id"),
        "document_versions",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_versions_workspace_id"),
        "document_versions",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_versions_document_id"),
        "document_versions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_versions_uploaded_by_user_id"),
        "document_versions",
        ["uploaded_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_versions_tenant_workspace_created_at"),
        "document_versions",
        ["tenant_id", "workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop document_versions table
    op.drop_index(
        op.f("ix_document_versions_tenant_workspace_created_at"),
        table_name="document_versions",
    )
    op.drop_index(
        op.f("ix_document_versions_uploaded_by_user_id"),
        table_name="document_versions",
    )
    op.drop_index(
        op.f("ix_document_versions_document_id"),
        table_name="document_versions",
    )
    op.drop_index(
        op.f("ix_document_versions_workspace_id"),
        table_name="document_versions",
    )
    op.drop_index(
        op.f("ix_document_versions_tenant_id"),
        table_name="document_versions",
    )
    op.drop_table("document_versions")

    # Drop documents table
    op.drop_index(
        op.f("ix_documents_tenant_workspace_created_at"),
        table_name="documents",
    )
    op.drop_index(
        op.f("ix_documents_created_by_user_id"),
        table_name="documents",
    )
    op.drop_index(
        op.f("ix_documents_workspace_id"),
        table_name="documents",
    )
    op.drop_index(
        op.f("ix_documents_tenant_id"),
        table_name="documents",
    )
    op.drop_table("documents")
