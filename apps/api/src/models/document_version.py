"""Document version model for document vault.

Each document can have multiple versions stored in S3.
Includes indexing status tracking for embeddings.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.tenant import Tenant
    from src.models.user import User
    from src.models.workspace import Workspace


class DocumentVersion(Base):
    """Document version model - represents a specific version of a document.

    Each version is stored in S3 and contains file metadata.
    Includes indexing status tracking for embedding generation.
    """

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "version_number", name="uq_document_versions_document_version"
        ),
        Index("ix_document_versions_tenant_id", "tenant_id"),
        Index("ix_document_versions_workspace_id", "workspace_id"),
        Index("ix_document_versions_document_id", "document_id"),
        Index("ix_document_versions_uploaded_by_user_id", "uploaded_by_user_id"),
        Index(
            "ix_document_versions_tenant_workspace_created_at",
            "tenant_id",
            "workspace_id",
            "created_at",
        ),
        Index("ix_document_versions_is_indexed", "is_indexed"),
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
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_provider: Mapped[str] = mapped_column(
        String, nullable=False
    )  # s3
    storage_bucket: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by_user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Indexing status tracking
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

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    uploaded_by: Mapped["User"] = relationship("User")
