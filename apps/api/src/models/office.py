"""Office document and WOPI token models."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class OfficeDocument(Base):
    """Office document stored in MinIO and edited through Collabora."""

    __tablename__ = "office_documents"
    __table_args__ = (
        Index("ix_office_documents_org_id", "org_id"),
        Index("ix_office_documents_owner_id", "owner_id"),
        Index("ix_office_documents_doc_type", "doc_type"),
        Index("ix_office_documents_org_title", "org_id", "title"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_modified_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
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

    organization = relationship("Organization", lazy="selectin")
    owner = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    last_modified_by_user = relationship("User", foreign_keys=[last_modified_by], lazy="selectin")
    wopi_tokens = relationship(
        "WopiToken",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class WopiToken(Base):
    """Short-lived token granting Collabora access to a single office document."""

    __tablename__ = "wopi_tokens"
    __table_args__ = (
        Index("ix_wopi_tokens_token", "token", unique=True),
        Index("ix_wopi_tokens_document_id", "document_id"),
        Index("ix_wopi_tokens_user_id", "user_id"),
        Index("ix_wopi_tokens_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("office_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    can_write: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped[OfficeDocument] = relationship("OfficeDocument", back_populates="wopi_tokens")
    user = relationship("User", lazy="selectin")
