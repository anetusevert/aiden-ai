"""Add office_documents and wopi_tokens tables.

Revision ID: 20260403_000002
Revises: 20260403_000001
Create Date: 2026-04-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260403_000002"
down_revision: Union[str, None] = "20260403_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "office_documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("doc_type", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_modified_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["last_modified_by"],
            ["users.id"],
            name=op.f("fk_office_documents_last_modified_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_office_documents_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_office_documents_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_office_documents")),
    )
    op.create_index(
        "ix_office_documents_org_id",
        "office_documents",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        "ix_office_documents_owner_id",
        "office_documents",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_office_documents_doc_type",
        "office_documents",
        ["doc_type"],
        unique=False,
    )
    op.create_index(
        "ix_office_documents_org_title",
        "office_documents",
        ["org_id", "title"],
        unique=False,
    )

    op.create_table(
        "wopi_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("can_write", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["office_documents.id"],
            name=op.f("fk_wopi_tokens_document_id_office_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_wopi_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wopi_tokens")),
    )
    op.create_index("ix_wopi_tokens_token", "wopi_tokens", ["token"], unique=True)
    op.create_index(
        "ix_wopi_tokens_document_id",
        "wopi_tokens",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_wopi_tokens_user_id",
        "wopi_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_wopi_tokens_expires_at",
        "wopi_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wopi_tokens_expires_at", table_name="wopi_tokens")
    op.drop_index("ix_wopi_tokens_user_id", table_name="wopi_tokens")
    op.drop_index("ix_wopi_tokens_document_id", table_name="wopi_tokens")
    op.drop_index("ix_wopi_tokens_token", table_name="wopi_tokens")
    op.drop_table("wopi_tokens")

    op.drop_index("ix_office_documents_org_title", table_name="office_documents")
    op.drop_index("ix_office_documents_doc_type", table_name="office_documents")
    op.drop_index("ix_office_documents_owner_id", table_name="office_documents")
    op.drop_index("ix_office_documents_org_id", table_name="office_documents")
    op.drop_table("office_documents")
