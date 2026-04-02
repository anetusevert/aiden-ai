"""Workspace schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    """Schema for creating a workspace."""

    name: str = Field(..., min_length=1, max_length=255)
    workspace_type: Literal["IN_HOUSE", "LAW_FIRM"] = Field(
        ..., description="Type of workspace"
    )
    jurisdiction_profile: Literal["UAE_DEFAULT", "DIFC_DEFAULT", "ADGM_DEFAULT", "KSA_DEFAULT"] = Field(
        ..., description="Jurisdiction profile for the workspace"
    )
    default_language: Literal["en", "ar", "mixed"] = Field(
        ..., description="Default language for the workspace"
    )


class WorkspaceResponse(BaseModel):
    """Schema for workspace response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    workspace_type: str
    jurisdiction_profile: str
    default_language: str
    policy_profile_id: str | None = None
    created_at: datetime
