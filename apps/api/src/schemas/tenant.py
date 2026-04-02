"""Tenant schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TenantCreate(BaseModel):
    """Schema for creating a tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    primary_jurisdiction: Literal["UAE", "KSA", "DIFC", "ADGM"] = Field(
        ..., description="Primary jurisdiction for the tenant"
    )
    data_residency_policy: Literal["UAE", "KSA", "GCC"] = Field(
        ..., description="Data residency policy"
    )


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    primary_jurisdiction: str
    data_residency_policy: str
    created_at: datetime


# ============================================================================
# Bootstrap Schemas
# ============================================================================


class BootstrapAdminUser(BaseModel):
    """Admin user info for bootstrap."""

    email: EmailStr = Field(..., description="Admin user email address")
    password: str = Field(..., min_length=8, description="Initial password for admin")
    full_name: str | None = Field(None, max_length=255)


class BootstrapWorkspace(BaseModel):
    """Workspace info for bootstrap."""

    name: str = Field(..., min_length=1, max_length=255)
    workspace_type: Literal["IN_HOUSE", "LAW_FIRM"] = Field(
        default="IN_HOUSE", description="Type of workspace"
    )
    jurisdiction_profile: Literal["UAE_DEFAULT", "DIFC_DEFAULT", "ADGM_DEFAULT", "KSA_DEFAULT"] = Field(
        default="UAE_DEFAULT", description="Jurisdiction profile"
    )
    default_language: Literal["en", "ar", "mixed"] = Field(
        default="en", description="Default language"
    )


class BootstrapPayload(BaseModel):
    """Optional bootstrap payload for tenant creation."""

    admin_user: BootstrapAdminUser
    workspace: BootstrapWorkspace


class TenantCreateWithBootstrap(BaseModel):
    """Schema for creating a tenant with optional bootstrap."""

    name: str = Field(..., min_length=1, max_length=255)
    primary_jurisdiction: Literal["UAE", "KSA", "DIFC", "ADGM"] = Field(
        ..., description="Primary jurisdiction for the tenant"
    )
    data_residency_policy: Literal["UAE", "KSA", "GCC"] = Field(
        ..., description="Data residency policy"
    )
    bootstrap: BootstrapPayload | None = Field(
        None, description="Optional bootstrap payload to create first admin user and workspace"
    )


class BootstrapResponse(BaseModel):
    """Response for tenant creation with bootstrap."""

    model_config = ConfigDict(from_attributes=True)

    tenant_id: str
    tenant_name: str
    workspace_id: str | None = None
    workspace_name: str | None = None
    admin_user_id: str | None = None
    admin_user_email: str | None = None
    created_at: datetime
