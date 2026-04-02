"""Document model for document vault.

Documents are workspace-scoped and support versioning.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.document_version import DocumentVersion
    from src.models.tenant import Tenant
    from src.models.user import User
    from src.models.workspace import Workspace


class Document(Base):
    """Document model - represents a document in the vault.

    Documents are workspace-scoped and tenant-isolated.
    Each document can have multiple versions.
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tenant_id", "tenant_id"),
        Index("ix_documents_workspace_id", "workspace_id"),
        Index("ix_documents_created_by_user_id", "created_by_user_id"),
        Index(
            "ix_documents_tenant_workspace_created_at",
            "tenant_id",
            "workspace_id",
            "created_at",
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
    title: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # contract, policy, memo, regulatory, other
    jurisdiction: Mapped[str] = mapped_column(
        String, nullable=False
    )  # UAE, DIFC, ADGM, KSA
    language: Mapped[str] = mapped_column(
        String, nullable=False
    )  # en, ar, mixed
    confidentiality: Mapped[str] = mapped_column(
        String, nullable=False
    )  # public, internal, confidential, highly_confidential
    created_by_user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="documents")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="documents")
    created_by: Mapped["User"] = relationship("User", back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number.desc()",
    )
