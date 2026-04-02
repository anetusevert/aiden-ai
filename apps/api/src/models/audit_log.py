"""Audit log model for enterprise compliance and debugging.

This is an append-only table. Records must never be updated or deleted.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class AuditLog(Base):
    """Append-only audit log for tracking all significant actions.

    This table stores a comprehensive audit trail of user actions for:
    - Enterprise compliance and trust
    - Debugging and support
    - Security monitoring

    Records should NEVER be updated or deleted. The table is append-only.
    """

    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Timestamp - when the action occurred
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Multi-tenancy context
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True,
    )

    # Request tracking
    request_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    # Action details
    action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    resource_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True,
    )

    # Outcome
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )

    # Additional context (avoid storing sensitive data)
    meta: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Request metadata
    ip: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Composite index for common query patterns
    __table_args__ = (
        # Tenant + action for finding specific actions within a tenant
        Index("ix_audit_logs_tenant_action", "tenant_id", "action"),
        # Tenant + created_at for time-based queries within a tenant
        Index("ix_audit_logs_tenant_created_at", "tenant_id", "created_at"),
        # Workspace + created_at for workspace-scoped time queries
        Index("ix_audit_logs_workspace_created_at", "workspace_id", "created_at"),
    )
