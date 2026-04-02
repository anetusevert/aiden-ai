"""User model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.database import Base
from src.utils.passwords import normalize_email

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.refresh_session import RefreshSession
    from src.models.tenant import Tenant
    from src.models.workspace_membership import WorkspaceMembership


class User(Base):
    """User model - represents an app-level user profile."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_tenant_id", "tenant_id"),
        Index("uq_users_email_normalized", "email_normalized", unique=True),
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
    email: Mapped[str] = mapped_column(String, nullable=False)
    email_normalized: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    default_workspace_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    # Token version for session revocation (increment to invalidate all tokens)
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    # Platform admin flag - allows managing global law corpus
    is_platform_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    @validates("email")
    def _sync_email_normalized(self, _key: str, address: str) -> str:
        object.__setattr__(self, "email_normalized", normalize_email(address))
        return address

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="created_by", cascade="all, delete-orphan"
    )
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        "RefreshSession", back_populates="user", cascade="all, delete-orphan"
    )
