"""Wiki models for the Amin Legal Wiki.

The wiki is a persistent, compounding knowledge base that sits between
HeyAmin's raw document sources and Amin's responses. Pages are LLM-authored
markdown, linked together to form a navigable legal knowledge graph.

Scoping:
- org_id=NULL  → global GCC legal wiki (shared across all organisations)
- org_id=<uuid> → organisation-private wiki pages
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


WIKI_CATEGORIES = frozenset({
    "law",
    "regulation",
    "concept",
    "entity",
    "case",
    "synthesis",
    "research",
})

WIKI_JURISDICTIONS = frozenset({
    "UAE",
    "KSA",
    "QATAR",
    "BAHRAIN",
    "OMAN",
    "KUWAIT",
    "GCC",
})

WIKI_OPERATIONS = frozenset({
    "ingest",
    "query",
    "lint",
    "update",
    "create",
})


class WikiPage(Base):
    """A single wiki page — LLM-authored markdown covering one legal topic.

    Pages are unique within their org scope (or globally when org_id is NULL).
    The slug is the human-readable identifier used in wiki-links.
    """

    __tablename__ = "wiki_pages"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_wiki_pages_org_slug"),
        Index("ix_wiki_pages_org_id", "org_id"),
        Index("ix_wiki_pages_category", "category"),
        Index("ix_wiki_pages_jurisdiction", "jurisdiction"),
        Index("ix_wiki_pages_is_stale", "is_stale"),
        Index("ix_wiki_pages_updated_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    org_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(String(300), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_doc_ids: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb",
    )
    inbound_link_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1",
    )
    is_stale: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    has_contradictions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    created_by_tool: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    outbound_links: Mapped[list["WikiLink"]] = relationship(
        "WikiLink",
        foreign_keys="WikiLink.from_page_id",
        back_populates="from_page",
        cascade="all, delete-orphan",
    )
    inbound_links: Mapped[list["WikiLink"]] = relationship(
        "WikiLink",
        foreign_keys="WikiLink.to_page_id",
        back_populates="to_page",
        cascade="all, delete-orphan",
    )


class WikiLink(Base):
    """Directed edge between two wiki pages.

    Captures the anchor text and a one-sentence rationale for why
    the pages are linked, enabling the knowledge graph to be self-documenting.
    """

    __tablename__ = "wiki_links"
    __table_args__ = (
        UniqueConstraint("from_page_id", "to_page_id", name="uq_wiki_links_from_to"),
        Index("ix_wiki_links_from_page_id", "from_page_id"),
        Index("ix_wiki_links_to_page_id", "to_page_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    from_page_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_page_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    link_text: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    from_page: Mapped["WikiPage"] = relationship(
        "WikiPage",
        foreign_keys=[from_page_id],
        back_populates="outbound_links",
    )
    to_page: Mapped["WikiPage"] = relationship(
        "WikiPage",
        foreign_keys=[to_page_id],
        back_populates="inbound_links",
    )


class WikiIndex(Base):
    """Auto-maintained index of all wiki pages for an organisation (or global).

    One row per org plus one global row (org_id=NULL). The content_md field
    is a markdown table/list of all pages with their summaries, rebuilt
    periodically so the LLM can quickly scan what the wiki already knows.
    """

    __tablename__ = "wiki_indexes"
    __table_args__ = (
        UniqueConstraint("org_id", name="uq_wiki_indexes_org_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    org_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    content_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="''")
    page_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    last_rebuilt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class WikiLog(Base):
    """Append-only audit trail for wiki operations.

    Every ingest, query, lint pass, or page update is recorded here so the
    team can debug wiki behaviour and track knowledge growth over time.
    """

    __tablename__ = "wiki_logs"
    __table_args__ = (
        Index("ix_wiki_logs_org_id", "org_id"),
        Index("ix_wiki_logs_operation", "operation"),
        Index("ix_wiki_logs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    org_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    page_slug: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    amin_summary: Mapped[str] = mapped_column(Text, nullable=False)
    pages_affected: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="'[]'::jsonb",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
