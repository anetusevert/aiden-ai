"""Policy profile model for tenant-level policy configurations."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.tenant import Tenant
    from src.models.workspace import Workspace


class PolicyProfile(Base):
    """Policy profile model - defines policy configurations for workspaces.

    Policy profiles are tenant-scoped and define what workflows, languages,
    jurisdictions, and features are allowed within workspaces that reference them.
    """

    __tablename__ = "policy_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_policy_profiles_tenant_name"),
        Index("ix_policy_profiles_tenant_id", "tenant_id"),
        Index("ix_policy_profiles_tenant_default", "tenant_id", "is_default"),
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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="policy_profiles")
    workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace", back_populates="policy_profile"
    )
