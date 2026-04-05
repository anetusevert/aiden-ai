"""Scraping job execution log — one row per connector run."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class ScrapingJob(Base):
    """Execution record for a single scraping connector run."""

    __tablename__ = "scraping_jobs"
    __table_args__ = (
        Index("ix_scraping_jobs_source_id", "source_id"),
        Index("ix_scraping_jobs_status", "status"),
        Index("ix_scraping_jobs_created_at_desc", "created_at", postgresql_using="btree"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("scraping_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    connector_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    triggered_by: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    items_listed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    items_upserted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    items_failed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    error_detail: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    run_log: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
