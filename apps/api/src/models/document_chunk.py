"""DocumentChunk model for storing text chunks from document versions.

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
    from src.models.document import Document
    from src.models.document_version import DocumentVersion
    from src.models.tenant import Tenant
    from src.models.workspace import Workspace


class DocumentChunk(Base):
    """DocumentChunk model - stores a text chunk from a document version.

    Chunks are deterministic and have stable character offsets for citations.
    Includes a generated tsvector column for PostgreSQL full-text search.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "chunk_index", name="uq_document_chunks_version_chunk_index"
        ),
        Index("ix_document_chunks_tenant_id", "tenant_id"),
        Index("ix_document_chunks_workspace_id", "workspace_id"),
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_version_id", "version_id"),
        Index(
            "ix_document_chunks_text_search_vector",
            "text_search_vector",
            postgresql_using="gin",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
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
    tenant: Mapped["Tenant"] = relationship("Tenant")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    document: Mapped["Document"] = relationship("Document")
    version: Mapped["DocumentVersion"] = relationship("DocumentVersion")
