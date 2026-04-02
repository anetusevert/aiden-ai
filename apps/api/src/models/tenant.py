"""Tenant model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.policy_profile import PolicyProfile
    from src.models.user import User
    from src.models.workspace import Workspace
    from src.models.workspace_membership import WorkspaceMembership


class Tenant(Base):
    """Tenant model - represents an organization in the system."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    primary_jurisdiction: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g., UAE, KSA, DIFC, ADGM
    data_residency_policy: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g., UAE, KSA, GCC
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace", back_populates="tenant", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership", back_populates="tenant", cascade="all, delete-orphan"
    )
    policy_profiles: Mapped[list["PolicyProfile"]] = relationship(
        "PolicyProfile", back_populates="tenant", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="tenant", cascade="all, delete-orphan"
    )
