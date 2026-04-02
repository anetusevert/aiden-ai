"""LegalChunkEmbedding model for storing vector embeddings of legal chunks.

Embeddings are stored using native pgvector vector(384) type for efficient
similarity search directly in PostgreSQL.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, Vector

if TYPE_CHECKING:
    from src.models.legal_chunk import LegalChunk
    from src.models.legal_instrument import LegalInstrument
    from src.models.legal_instrument_version import LegalInstrumentVersion


class LegalChunkEmbedding(Base):
    """LegalChunkEmbedding model - stores vector embeddings for legal chunks.

    Each chunk has at most one embedding. Embeddings are stored as native
    pgvector vector(384) type for efficient PostgreSQL-native similarity search.
    """

    __tablename__ = "legal_chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", name="uq_legal_chunk_embeddings_chunk_id"),
        Index("ix_legal_chunk_embeddings_instrument_id", "instrument_id"),
        Index("ix_legal_chunk_embeddings_version_id", "version_id"),
        Index("ix_legal_chunk_embeddings_chunk_id", "chunk_id", unique=True),
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
    chunk_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("legal_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Embedding stored as native pgvector vector(384) for efficient similarity search
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    # Model identifier for tracking which model generated the embedding
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    instrument: Mapped["LegalInstrument"] = relationship("LegalInstrument")
    version: Mapped["LegalInstrumentVersion"] = relationship("LegalInstrumentVersion")
    chunk: Mapped["LegalChunk"] = relationship(
        "LegalChunk",
        back_populates="embedding",
    )
