"""Add news_items table for persistent legal news storage.

Revision ID: 20260406_000002
Revises: 20260406_000001
Create Date: 2026-04-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260406_000002"
down_revision: Union[str, None] = "20260406_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "news_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("external_id", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("title_ar", sa.String(1000), nullable=True),
        sa.Column("summary", sa.String(500), nullable=True),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("image_url", sa.String(2000), nullable=True),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_category", sa.String(100), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "wiki_filed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("wiki_page_slug", sa.String(300), nullable=True),
        sa.Column("amin_summary", sa.String(500), nullable=True),
        sa.Column(
            "importance",
            sa.String(20),
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=True,
            server_default="[]",
        ),
    )

    op.create_index(
        "ix_news_items_external_id", "news_items", ["external_id"], unique=True,
    )
    op.create_index(
        "ix_news_items_source_name", "news_items", ["source_name"],
    )
    op.create_index(
        "ix_news_items_source_category", "news_items", ["source_category"],
    )
    op.create_index(
        "ix_news_items_jurisdiction", "news_items", ["jurisdiction"],
    )
    op.create_index(
        "ix_news_items_published_at_desc",
        "news_items",
        [sa.text("published_at DESC")],
    )
    op.create_index(
        "ix_news_items_wiki_filed", "news_items", ["wiki_filed"],
    )
    op.create_index(
        "ix_news_items_importance", "news_items", ["importance"],
    )


def downgrade() -> None:
    op.drop_index("ix_news_items_importance", table_name="news_items")
    op.drop_index("ix_news_items_wiki_filed", table_name="news_items")
    op.drop_index("ix_news_items_published_at_desc", table_name="news_items")
    op.drop_index("ix_news_items_jurisdiction", table_name="news_items")
    op.drop_index("ix_news_items_source_category", table_name="news_items")
    op.drop_index("ix_news_items_source_name", table_name="news_items")
    op.drop_index("ix_news_items_external_id", table_name="news_items")
    op.drop_table("news_items")
