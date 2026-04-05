"""Scraping source registry — one row per configured connector."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class ScrapingSource(Base):
    """Persistent configuration for a single harvester connector."""

    __tablename__ = "scraping_sources"
    __table_args__ = (
        Index("ix_scraping_sources_connector_name", "connector_name"),
        Index("ix_scraping_sources_enabled", "enabled"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    connector_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(200), nullable=False,
    )
    jurisdiction: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true",
    )
    schedule_cron: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    harvest_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="500",
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_job_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )
