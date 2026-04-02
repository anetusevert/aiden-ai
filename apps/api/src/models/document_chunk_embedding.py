"""DocumentChunkEmbedding model for storing vector embeddings of document chunks.

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
    from src.models.document import Document
    from src.models.document_chunk import DocumentChunk
    from src.models.document_version import DocumentVersion
    from src.models.tenant import Tenant
    from src.models.workspace import Workspace


class DocumentChunkEmbedding(Base):
    """DocumentChunkEmbedding model - stores vector embeddings for document chunks.

    Each chunk has at most one embedding. Embeddings are stored as native
    pgvector vector(384) type for efficient PostgreSQL-native similarity search.
    """

    __tablename__ = "document_chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", name="uq_document_chunk_embeddings_chunk_id"),
        Index("ix_document_chunk_embeddings_tenant_id", "tenant_id"),
        Index("ix_document_chunk_embeddings_workspace_id", "workspace_id"),
        Index("ix_document_chunk_embeddings_document_id", "document_id"),
        Index("ix_document_chunk_embeddings_version_id", "version_id"),
        Index("ix_document_chunk_embeddings_chunk_id", "chunk_id", unique=True),
        Index(
            "ix_document_chunk_embeddings_tenant_workspace",
            "tenant_id",
            "workspace_id",
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
    chunk_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
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
    tenant: Mapped["Tenant"] = relationship("Tenant")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    document: Mapped["Document"] = relationship("Document")
    version: Mapped["DocumentVersion"] = relationship("DocumentVersion")
    chunk: Mapped["DocumentChunk"] = relationship("DocumentChunk")
