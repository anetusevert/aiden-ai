"""Pydantic schemas for audit log endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """Response schema for a single audit log entry."""

    id: str = Field(..., description="Unique identifier for the audit log entry")
    created_at: datetime = Field(..., description="When the action occurred")
    tenant_id: str = Field(..., description="Tenant ID")
    workspace_id: str | None = Field(None, description="Workspace ID (if applicable)")
    user_id: str | None = Field(None, description="User ID who performed the action")
    request_id: str = Field(..., description="Request ID for tracing")
    action: str = Field(..., description="Action identifier (e.g., 'tenant.create')")
    resource_type: str | None = Field(None, description="Type of resource affected")
    resource_id: str | None = Field(None, description="ID of the affected resource")
    status: str = Field(..., description="Outcome status ('success' or 'fail')")
    meta: dict[str, Any] | None = Field(
        None, description="Additional structured context"
    )
    ip: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client User-Agent")

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Response schema for listing audit logs."""

    items: list[AuditLogResponse] = Field(..., description="List of audit log entries")
    total: int = Field(..., description="Total count of matching entries")
    limit: int = Field(..., description="Maximum entries returned")
