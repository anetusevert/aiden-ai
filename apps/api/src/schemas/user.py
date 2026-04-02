"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a user."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str | None = Field(None, max_length=255)
    password: str | None = Field(
        None,
        min_length=8,
        description="Optional initial password (required for password login)",
    )


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    email: str
    full_name: str | None
    is_active: bool
    is_platform_admin: bool = False
    created_at: datetime
