"""LegalInstrument model for global law corpus.

Legal instruments represent laws, regulations, decrees, etc. from GCC jurisdictions.
These are globally accessible and NOT tenant-scoped.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.legal_instrument_version import LegalInstrumentVersion
    from src.models.user import User


# Valid jurisdiction values for global legal corpus
LEGAL_JURISDICTIONS = frozenset({
    "UAE",
    "DIFC",
    "ADGM",
    "KSA",
    "OMAN",
    "BAHRAIN",
    "QATAR",
    "KUWAIT",
})

# Valid instrument type values
LEGAL_INSTRUMENT_TYPES = frozenset({
    "law",
    "federal_law",
    "local_law",
    "decree",
    "royal_decree",
    "regulation",
    "ministerial_resolution",
    "circular",
    "guideline",
    "directive",
    "order",
    "other",
})

# Valid status values
LEGAL_INSTRUMENT_STATUS = frozenset({
    "active",
    "superseded",
    "repealed",
    "draft",
})


class LegalInstrument(Base):
    """LegalInstrument model - represents a law/regulation in the global corpus.

    Legal instruments are NOT tenant-scoped. They are globally accessible
    baseline evidence for all tenants.
    """

    __tablename__ = "legal_instruments"
    __table_args__ = (
        Index("ix_legal_instruments_jurisdiction", "jurisdiction"),
        Index("ix_legal_instruments_instrument_type", "instrument_type"),
        Index("ix_legal_instruments_status", "status"),
        Index("ix_legal_instruments_created_at", "created_at"),
        Index("ix_legal_instruments_instrument_key", "instrument_key"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    jurisdiction: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    instrument_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="active",
    )
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
    created_by_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Snapshot import fields for idempotent bulk ingestion
    instrument_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Dedupe key: {jurisdiction}:{source_name}:{sha256(source_url)[:16]}",
    )
    import_batch_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="UUID of the snapshot import batch that created/updated this instrument",
    )

    # Relationships
    versions: Mapped[list["LegalInstrumentVersion"]] = relationship(
        "LegalInstrumentVersion",
        back_populates="instrument",
        cascade="all, delete-orphan",
        order_by="LegalInstrumentVersion.created_at.desc()",
    )
    created_by: Mapped["User | None"] = relationship("User")
