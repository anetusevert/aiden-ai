"""Persistent news item — one row per legal news article or update."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class NewsItem(Base):
    """A single legal news item scraped from a primary or RSS source."""

    __tablename__ = "news_items"
    __table_args__ = (
        Index("ix_news_items_external_id", "external_id", unique=True),
        Index("ix_news_items_source_name", "source_name"),
        Index("ix_news_items_source_category", "source_category"),
        Index("ix_news_items_jurisdiction", "jurisdiction"),
        Index("ix_news_items_published_at_desc", "published_at", postgresql_using="btree"),
        Index("ix_news_items_wiki_filed", "wiki_filed"),
        Index("ix_news_items_importance", "importance"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    external_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True,
    )
    title: Mapped[str] = mapped_column(
        String(1000), nullable=False,
    )
    title_ar: Mapped[str | None] = mapped_column(
        String(1000), nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    content_md: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    url: Mapped[str] = mapped_column(
        String(2000), nullable=False,
    )
    image_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True,
    )
    source_name: Mapped[str] = mapped_column(
        String(200), nullable=False,
    )
    source_category: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    jurisdiction: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    wiki_filed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    wiki_page_slug: Mapped[str | None] = mapped_column(
        String(300), nullable=True,
    )
    amin_summary: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    importance: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="normal",
    )
    tags: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, server_default="[]",
    )
