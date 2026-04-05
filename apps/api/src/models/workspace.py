"""Workspace model."""

from datetime import datetime
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.policy_profile import PolicyProfile
    from src.models.tenant import Tenant
    from src.models.workspace_membership import WorkspaceMembership


class Workspace(Base):
    """Workspace model - represents a workspace within a tenant."""

    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_workspaces_tenant_name"),
        Index("ix_workspaces_tenant_id", "tenant_id"),
        Index("ix_workspaces_policy_profile_id", "policy_profile_id"),
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
    name: Mapped[str] = mapped_column(String, nullable=False)
    workspace_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # IN_HOUSE | LAW_FIRM
    jurisdiction_profile: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g., UAE_DEFAULT, DIFC_DEFAULT
    default_language: Mapped[str] = mapped_column(
        String, nullable=False
    )  # en | ar | mixed
    policy_profile_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("policy_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="workspaces")
    memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership", back_populates="workspace", cascade="all, delete-orphan"
    )
    policy_profile: Mapped["PolicyProfile | None"] = relationship(
        "PolicyProfile", back_populates="workspaces"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="workspace", cascade="all, delete-orphan"
    )
