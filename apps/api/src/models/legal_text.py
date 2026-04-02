"""LegalText model for storing extracted text from legal instrument versions.

Stores the full extracted text from PDFs and DOCX files.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.legal_instrument_version import LegalInstrumentVersion


class LegalText(Base):
    """LegalText model - stores extracted text for a legal instrument version.

    Each legal instrument version can have one extracted text record.
    Text is stored as-is from extraction.
    """

    __tablename__ = "legal_texts"
    __table_args__ = (
        Index("ix_legal_texts_version_id", "version_id", unique=True),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("legal_instrument_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )  # "pymupdf" | "pdfminer" | "docx"
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    version: Mapped["LegalInstrumentVersion"] = relationship(
        "LegalInstrumentVersion",
        back_populates="text",
    )
