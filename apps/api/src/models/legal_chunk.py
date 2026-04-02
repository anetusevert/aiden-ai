"""LegalChunk model for storing text chunks from legal instrument versions.

Chunks are stable pieces of extracted text with character offsets.
Includes full-text search support via tsvector column.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Computed, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.legal_chunk_embedding import LegalChunkEmbedding
    from src.models.legal_instrument import LegalInstrument
    from src.models.legal_instrument_version import LegalInstrumentVersion


class LegalChunk(Base):
    """LegalChunk model - stores a text chunk from a legal instrument version.

    Chunks are deterministic and have stable character offsets for citations.
    Includes a generated tsvector column for PostgreSQL full-text search.
    """

    __tablename__ = "legal_chunks"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "chunk_index", name="uq_legal_chunks_version_chunk_index"
        ),
        Index("ix_legal_chunks_instrument_id", "instrument_id"),
        Index("ix_legal_chunks_version_id", "version_id"),
        Index(
            "ix_legal_chunks_text_search_vector",
            "text_search_vector",
            postgresql_using="gin",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    instrument_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("legal_instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("legal_instrument_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 0..n-1
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Generated tsvector column for full-text search (computed from text)
    text_search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', text)", persisted=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    instrument: Mapped["LegalInstrument"] = relationship("LegalInstrument")
    version: Mapped["LegalInstrumentVersion"] = relationship(
        "LegalInstrumentVersion",
        back_populates="chunks",
    )
    embedding: Mapped["LegalChunkEmbedding | None"] = relationship(
        "LegalChunkEmbedding",
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan",
    )
