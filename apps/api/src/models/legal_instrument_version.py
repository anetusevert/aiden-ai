"""LegalInstrumentVersion model for global law corpus.

Each legal instrument can have multiple versions stored in S3.
Includes indexing status tracking for embeddings.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.legal_chunk import LegalChunk
    from src.models.legal_instrument import LegalInstrument
    from src.models.legal_text import LegalText
    from src.models.user import User


class LegalInstrumentVersion(Base):
    """LegalInstrumentVersion model - represents a specific version of a legal instrument.

    Each version is stored in S3 and contains file metadata.
    Includes indexing status tracking for embedding generation.
    """

    __tablename__ = "legal_instrument_versions"
    __table_args__ = (
        Index("ix_legal_instrument_versions_legal_instrument_id", "legal_instrument_id"),
        Index("ix_legal_instrument_versions_is_indexed", "is_indexed"),
        Index("ix_legal_instrument_versions_language", "language"),
        Index("ix_legal_instrument_versions_created_at", "created_at"),
        Index("ix_legal_instrument_versions_version_key", "version_key"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    legal_instrument_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("legal_instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_label: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    storage_bucket: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    extracted_text_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    is_indexed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    embedding_model: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    uploaded_by_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Snapshot import fields for idempotent bulk ingestion
    version_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Dedupe key: raw_sha256 from harvester snapshot",
    )
    import_batch_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="UUID of the snapshot import batch that created this version",
    )
    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when this version was imported from a snapshot",
    )

    # Relationships
    instrument: Mapped["LegalInstrument"] = relationship(
        "LegalInstrument",
        back_populates="versions",
    )
    uploaded_by: Mapped["User | None"] = relationship("User")
    text: Mapped["LegalText | None"] = relationship(
        "LegalText",
        back_populates="version",
        uselist=False,
        cascade="all, delete-orphan",
    )
    chunks: Mapped[list["LegalChunk"]] = relationship(
        "LegalChunk",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="LegalChunk.chunk_index",
    )
