"""Workspace Membership schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class WorkspaceMembershipCreate(BaseModel):
    """Schema for creating a workspace membership (by user_id)."""

    user_id: str = Field(..., description="User ID to add to workspace")
    role: Literal["ADMIN", "EDITOR", "VIEWER"] = Field(
        ..., description="Role for the user in the workspace"
    )


class MemberInviteRequest(BaseModel):
    """Schema for inviting a member by email."""

    email: EmailStr = Field(..., description="Email of the user to invite")
    full_name: str | None = Field(
        None, description="Optional full name for new users"
    )
    initial_password: str | None = Field(
        None,
        min_length=8,
        description="Required when creating a new user (password login)",
    )
    role: Literal["ADMIN", "EDITOR", "VIEWER"] = Field(
        ..., description="Role for the user in the workspace"
    )


class MemberRoleUpdateRequest(BaseModel):
    """Schema for updating a member's role."""

    role: Literal["ADMIN", "EDITOR", "VIEWER"] = Field(
        ..., description="New role for the member"
    )


class WorkspaceMembershipResponse(BaseModel):
    """Schema for workspace membership response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workspace_id: str
    user_id: str
    role: str
    created_at: datetime


class MemberWithUserResponse(BaseModel):
    """Schema for membership with user details."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workspace_id: str
    user_id: str
    role: str
    created_at: datetime
    # User details
    email: str | None = None
    full_name: str | None = None
    is_active: bool = True

    @classmethod
    def from_membership(cls, membership) -> "MemberWithUserResponse":
        """Create from membership with loaded user relationship."""
        return cls(
            id=membership.id,
            tenant_id=membership.tenant_id,
            workspace_id=membership.workspace_id,
            user_id=membership.user_id,
            role=membership.role,
            created_at=membership.created_at,
            email=membership.user.email if membership.user else None,
            full_name=membership.user.full_name if membership.user else None,
            is_active=membership.user.is_active if membership.user else True,
        )
