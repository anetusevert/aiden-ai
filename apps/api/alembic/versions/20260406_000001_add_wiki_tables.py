"""Add wiki tables (wiki_pages, wiki_links, wiki_indexes, wiki_logs).

Revision ID: 20260406_000001
Revises: 20260404_000001
Create Date: 2026-04-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260406_000001"
down_revision: Union[str, None] = "20260404_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── wiki_pages ──────────────────────────────────────────────────────
    op.create_table(
        "wiki_pages",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("slug", sa.String(300), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.String(32), nullable=True),
        sa.Column(
            "source_doc_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("inbound_link_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_contradictions", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by_tool", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_wiki_pages_org_id", "wiki_pages", ["org_id"])
    op.create_index("ix_wiki_pages_category", "wiki_pages", ["category"])
    op.create_index("ix_wiki_pages_jurisdiction", "wiki_pages", ["jurisdiction"])
    op.create_index("ix_wiki_pages_is_stale", "wiki_pages", ["is_stale"])
    op.create_index("ix_wiki_pages_updated_at", "wiki_pages", ["updated_at"])
    op.create_unique_constraint("uq_wiki_pages_org_slug", "wiki_pages", ["org_id", "slug"])

    # ── wiki_links ──────────────────────────────────────────────────────
    op.create_table(
        "wiki_links",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "from_page_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("wiki_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_page_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("wiki_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("link_text", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_wiki_links_from_page_id", "wiki_links", ["from_page_id"])
    op.create_index("ix_wiki_links_to_page_id", "wiki_links", ["to_page_id"])
    op.create_unique_constraint("uq_wiki_links_from_to", "wiki_links", ["from_page_id", "to_page_id"])

    # ── wiki_indexes ────────────────────────────────────────────────────
    op.create_table(
        "wiki_indexes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("content_md", sa.Text(), nullable=False, server_default="''"),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_rebuilt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_unique_constraint("uq_wiki_indexes_org_id", "wiki_indexes", ["org_id"])

    # ── wiki_logs ───────────────────────────────────────────────────────
    op.create_table(
        "wiki_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("page_slug", sa.String(300), nullable=True),
        sa.Column("source_description", sa.Text(), nullable=False),
        sa.Column("amin_summary", sa.Text(), nullable=False),
        sa.Column(
            "pages_affected",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_wiki_logs_org_id", "wiki_logs", ["org_id"])
    op.create_index("ix_wiki_logs_operation", "wiki_logs", ["operation"])
    op.create_index("ix_wiki_logs_created_at", "wiki_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("wiki_logs")
    op.drop_table("wiki_indexes")
    op.drop_table("wiki_links")
    op.drop_table("wiki_pages")
