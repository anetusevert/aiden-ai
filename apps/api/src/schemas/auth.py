"""Authentication schemas for Aiden.ai API."""

from typing import Literal

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Email + password sign-in (production path)."""

    email: EmailStr
    password: str


class DevLoginRequest(BaseModel):
    """Request body for dev login endpoint.

    Used for passwordless development authentication.
    Requires valid tenant, workspace, and user email.
    """

    tenant_id: str
    workspace_id: str
    email: EmailStr


class TokenResponse(BaseModel):
    """Response containing JWT access token (legacy)."""

    access_token: str
    token_type: str = "bearer"


class CookieAuthResponse(BaseModel):
    """Response for cookie-based authentication.

    Cookies are set via Set-Cookie headers.
    This body provides metadata about the session.
    """

    user_id: str
    email: str | None
    role: str
    expires_in: int  # Access token expiry in seconds
    auth_mode: Literal["cookie"] = "cookie"


class RefreshResponse(BaseModel):
    """Response for /auth/refresh endpoint.

    New cookies are set via Set-Cookie headers.
    """

    expires_in: int  # Access token expiry in seconds
    auth_mode: Literal["cookie"] = "cookie"


class CurrentUserResponse(BaseModel):
    """Response for /auth/me endpoint.

    Returns the authenticated user's identity and context.
    """

    user_id: str
    tenant_id: str
    workspace_id: str
    role: str
    email: str | None = None
    full_name: str | None = None
    is_platform_admin: bool = False
    auth_mode: Literal["cookie", "bearer"] = "cookie"
