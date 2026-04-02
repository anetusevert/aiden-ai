"""DocumentText model for storing extracted text from document versions.

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
    from src.models.document import Document
    from src.models.document_version import DocumentVersion
    from src.models.tenant import Tenant
    from src.models.workspace import Workspace


class DocumentText(Base):
    """DocumentText model - stores extracted text for a document version.

    Each document version can have one extracted text record.
    Text is stored as-is from extraction (no reshaping for Arabic, etc.).
    """

    __tablename__ = "document_texts"
    __table_args__ = (
        Index("ix_document_texts_tenant_id", "tenant_id"),
        Index("ix_document_texts_workspace_id", "workspace_id"),
        Index("ix_document_texts_document_id", "document_id"),
        Index("ix_document_texts_version_id", "version_id", unique=True),
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
        unique=True,
    )
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # "pymupdf" | "pdfminer" | "docx"
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
