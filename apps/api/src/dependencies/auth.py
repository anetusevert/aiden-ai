"""Authentication and authorization dependencies.

This module provides authentication via:
1. Cookie: access_token cookie (preferred, httpOnly)
2. Header: Authorization: Bearer <token> (fallback, dev only when ENVIRONMENT=dev)
3. Legacy: X-Tenant-Id, X-Workspace-Id, X-User-Id headers (for debugging)

The AUTH_MODE setting controls the legacy behavior:
- "jwt": Uses JWT tokens (via cookie or header)
- "headers": Uses X-*-Id headers (for debugging)

Every request is scoped by tenant_id and workspace_id from the auth context.
Centralized RequestContext provides a single point of access for auth state.
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models import Tenant, User, Workspace, WorkspaceMembership
from src.utils.jwt import (
    InvalidTokenError,
    JWTPayload,
    TokenExpiredError,
    TokenTypeMismatchError,
    decode_access_token,
)

# Role hierarchy: ADMIN > EDITOR > VIEWER
ROLE_HIERARCHY = {"ADMIN": 3, "EDITOR": 2, "VIEWER": 1}

# Optional Bearer token security scheme (doesn't require token, allows header fallback)
bearer_scheme = HTTPBearer(auto_error=False)


def validate_uuid(value: str, header_name: str) -> str:
    """Validate that a string is a valid UUID."""
    try:
        UUID(value)
        return value
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format for {header_name}",
        )


@dataclass
class RequestContext:
    """Centralized auth context for requests.

    Contains the authenticated tenant, user, and optionally workspace/membership.
    All privilege checks should use this context.
    """

    tenant: Tenant
    user: User
    workspace: Workspace | None = None
    membership: WorkspaceMembership | None = None

    @property
    def role(self) -> str | None:
        """Get the user's role in the current workspace."""
        return self.membership.role if self.membership else None

    def has_role(self, minimum_role: str) -> bool:
        """Check if user has at least the specified role."""
        if not self.membership:
            return False
        user_level = ROLE_HIERARCHY.get(self.membership.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)
        return user_level >= required_level


# ============================================================================
# JWT Token Extraction
# ============================================================================


@dataclass
class AuthCredentials:
    """Credentials extracted from either JWT or headers.

    This intermediate structure allows dual-mode authentication
    while presenting a unified interface to the entity loaders.
    """

    tenant_id: str
    user_id: str
    workspace_id: str | None = None
    role: str | None = None  # Only available from JWT


async def get_jwt_payload(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    access_token: Annotated[str | None, Cookie()] = None,
) -> JWTPayload | None:
    """Extract and validate JWT from cookie or Authorization header.

    Priority:
    1. Cookie: access_token (preferred, httpOnly)
    2. Header: Authorization: Bearer <token> (dev fallback only)

    Returns None if no token is provided (allows fallback to legacy headers).
    Raises 401 if token is provided but invalid/expired.

    Note: Header fallback is only allowed when ENVIRONMENT=dev.
    In staging/prod, only cookie auth is accepted.
    """
    token: str | None = None

    # Priority 1: Cookie access token
    if access_token:
        token = access_token
    # Priority 2: Header (dev only)
    elif credentials and settings.environment == "dev":
        token = credentials.credentials
    elif credentials and settings.environment != "dev":
        # In non-dev, header auth is not allowed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "header_auth_disabled",
                "message": "Authorization header auth is only allowed in dev environment. Use cookie auth.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token is None:
        return None

    try:
        return decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "token_expired",
                "message": "Access token has expired. Please refresh or sign in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenTypeMismatchError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "invalid_token_type",
                "message": "Invalid token type. Expected access token.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "invalid_token",
                "message": str(e),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# Header Extraction Dependencies (Legacy/Debug Mode)
# ============================================================================


async def get_optional_tenant_header(
    x_tenant_id: Annotated[str | None, Header()] = None,
) -> str | None:
    """Extract X-Tenant-Id header if present."""
    if x_tenant_id:
        return validate_uuid(x_tenant_id, "X-Tenant-Id")
    return None


async def get_tenant_header(
    x_tenant_id: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and validate X-Tenant-Id header (required)."""
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header is required",
        )
    return validate_uuid(x_tenant_id, "X-Tenant-Id")


async def get_workspace_header(
    x_workspace_id: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and validate X-Workspace-Id header (required)."""
    if not x_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Workspace-Id header is required",
        )
    return validate_uuid(x_workspace_id, "X-Workspace-Id")


async def get_optional_workspace_header(
    x_workspace_id: Annotated[str | None, Header()] = None,
) -> str | None:
    """Extract X-Workspace-Id header if present."""
    if x_workspace_id:
        return validate_uuid(x_workspace_id, "X-Workspace-Id")
    return None


async def get_user_id_header(
    x_user_id: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and validate X-User-Id header (required)."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id header is required",
        )
    return validate_uuid(x_user_id, "X-User-Id")


async def get_optional_user_id_header(
    x_user_id: Annotated[str | None, Header()] = None,
) -> str | None:
    """Extract X-User-Id header if present."""
    if x_user_id:
        return validate_uuid(x_user_id, "X-User-Id")
    return None


# ============================================================================
# Unified Auth Credentials Extraction
# ============================================================================


async def get_auth_credentials(
    jwt_payload: Annotated[JWTPayload | None, Depends(get_jwt_payload)],
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    x_workspace_id: Annotated[str | None, Header()] = None,
) -> AuthCredentials:
    """Get authentication credentials from JWT (cookie/header) or legacy headers.

    In JWT mode (default):
    - Prefers access_token cookie (httpOnly)
    - Falls back to Authorization header in dev environment only
    - Extracts tenant_id, user_id, workspace_id, role from token claims

    In headers mode (legacy/debug):
    - Requires X-Tenant-Id, X-User-Id headers
    - X-Workspace-Id is optional at this stage

    Returns AuthCredentials for use by entity loaders.
    """
    if settings.auth_mode == "jwt":
        # JWT mode: require valid token (cookie or header)
        if jwt_payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "authentication_required",
                    "message": "Authentication required. Please sign in.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        return AuthCredentials(
            tenant_id=jwt_payload.tenant_id,
            user_id=jwt_payload.sub,
            workspace_id=jwt_payload.workspace_id,
            role=jwt_payload.role,
        )
    else:
        # Headers mode: extract from X-* headers
        if not x_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-Id header is required",
            )
        if not x_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-User-Id header is required",
            )
        return AuthCredentials(
            tenant_id=validate_uuid(x_tenant_id, "X-Tenant-Id"),
            user_id=validate_uuid(x_user_id, "X-User-Id"),
            workspace_id=validate_uuid(x_workspace_id, "X-Workspace-Id")
            if x_workspace_id
            else None,
        )


async def get_workspace_auth_credentials(
    jwt_payload: Annotated[JWTPayload | None, Depends(get_jwt_payload)],
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    x_workspace_id: Annotated[str | None, Header()] = None,
) -> AuthCredentials:
    """Get auth credentials with workspace_id required.

    Same as get_auth_credentials but ensures workspace_id is present.
    """
    if settings.auth_mode == "jwt":
        if jwt_payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "authentication_required",
                    "message": "Authentication required. Please sign in.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not jwt_payload.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token missing workspace_id claim",
            )
        return AuthCredentials(
            tenant_id=jwt_payload.tenant_id,
            user_id=jwt_payload.sub,
            workspace_id=jwt_payload.workspace_id,
            role=jwt_payload.role,
        )
    else:
        if not x_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-Id header is required",
            )
        if not x_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-User-Id header is required",
            )
        if not x_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Workspace-Id header is required",
            )
        return AuthCredentials(
            tenant_id=validate_uuid(x_tenant_id, "X-Tenant-Id"),
            user_id=validate_uuid(x_user_id, "X-User-Id"),
            workspace_id=validate_uuid(x_workspace_id, "X-Workspace-Id"),
        )


# ============================================================================
# Entity Loading Dependencies (Updated for dual-mode auth)
# ============================================================================


async def get_current_tenant(
    tenant_id: Annotated[str, Depends(get_tenant_header)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    """Get and validate current tenant from header.

    Note: This is a legacy dependency. New code should use get_tenant_context
    or get_workspace_context which handle both JWT and header auth modes.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return tenant


async def get_current_user(
    user_id: Annotated[str, Depends(get_user_id_header)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get and validate current user from header.

    Ensures the user belongs to the current tenant and is active.
    Prevents privilege escalation across tenants.

    Note: This is a legacy dependency for header mode.
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant.id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found or does not belong to tenant",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


async def get_current_workspace(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    """Get and validate current workspace from header.

    Ensures the workspace belongs to the current tenant.

    Note: This is a legacy dependency for header mode.
    """
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.tenant_id == tenant.id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace not found or does not belong to tenant",
        )
    return workspace


async def get_current_membership(
    user: Annotated[User, Depends(get_current_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceMembership:
    """Get current user's membership in the workspace.

    Note: This is a legacy dependency for header mode.
    """
    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this workspace",
        )
    return membership


# ============================================================================
# Unified Entity Loading (supports both JWT and header modes)
# ============================================================================


async def load_tenant_by_id(
    tenant_id: str,
    db: AsyncSession,
) -> Tenant:
    """Load and validate tenant by ID."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return tenant


async def load_user_by_id(
    user_id: str,
    tenant_id: str,
    db: AsyncSession,
    token_version: int | None = None,
) -> User:
    """Load user by ID, ensuring they belong to the tenant and are active.

    Args:
        user_id: The user ID to load
        tenant_id: The tenant ID the user must belong to
        db: Async database session
        token_version: If provided, validates that user.token_version matches

    Returns:
        The loaded User object

    Raises:
        HTTPException: If user not found, inactive, or token_version mismatch
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found or does not belong to tenant",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    # Validate token_version for session revocation
    if token_version is not None and user.token_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "token_revoked",
                "message": "Your session has been revoked. Please sign in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def load_workspace_by_id(
    workspace_id: str,
    tenant_id: str,
    db: AsyncSession,
) -> Workspace:
    """Load workspace by ID, ensuring it belongs to the tenant."""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.tenant_id == tenant_id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace not found or does not belong to tenant",
        )
    return workspace


async def load_membership(
    user_id: str,
    workspace_id: str,
    db: AsyncSession,
) -> WorkspaceMembership:
    """Load user's membership in a workspace."""
    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this workspace",
        )
    return membership


# ============================================================================
# Request Context Dependencies (Dual-mode: JWT or Headers)
# ============================================================================


async def get_tenant_context(
    auth: Annotated[AuthCredentials, Depends(get_auth_credentials)],
    jwt_payload: Annotated[JWTPayload | None, Depends(get_jwt_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestContext:
    """Get request context for tenant-scoped operations (no workspace required).

    Supports both JWT and header authentication based on AUTH_MODE setting.
    Use this for operations that only need tenant + user validation.
    """
    tenant = await load_tenant_by_id(auth.tenant_id, db)
    # Pass token_version for validation if using JWT mode
    token_version = jwt_payload.token_version if jwt_payload else None
    user = await load_user_by_id(auth.user_id, auth.tenant_id, db, token_version)
    return RequestContext(tenant=tenant, user=user)


async def get_workspace_context(
    auth: Annotated[AuthCredentials, Depends(get_workspace_auth_credentials)],
    jwt_payload: Annotated[JWTPayload | None, Depends(get_jwt_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestContext:
    """Get full request context for workspace-scoped operations.

    Supports both JWT and header authentication based on AUTH_MODE setting.
    Use this for operations that need full tenant + workspace + membership validation.

    In JWT mode, additionally validates that:
    - User is still active (token may have been issued before deactivation)
    - User still has membership in workspace (membership may have been removed)
    - Token version matches user.token_version (for session revocation)
    """
    tenant = await load_tenant_by_id(auth.tenant_id, db)
    # Pass token_version for validation if using JWT mode
    token_version = jwt_payload.token_version if jwt_payload else None
    user = await load_user_by_id(auth.user_id, auth.tenant_id, db, token_version)

    # workspace_id is guaranteed by get_workspace_auth_credentials
    assert auth.workspace_id is not None
    workspace = await load_workspace_by_id(auth.workspace_id, auth.tenant_id, db)
    membership = await load_membership(auth.user_id, auth.workspace_id, db)

    return RequestContext(
        tenant=tenant,
        user=user,
        workspace=workspace,
        membership=membership,
    )


# ============================================================================
# Role Checker Dependencies
# ============================================================================


class RoleChecker:
    """Dependency factory for role-based access control."""

    def __init__(self, minimum_role: str):
        self.minimum_role = minimum_role
        self.minimum_level = ROLE_HIERARCHY.get(minimum_role, 0)

    async def __call__(
        self,
        ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    ) -> RequestContext:
        """Check if user has the required role."""
        if not ctx.membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this workspace",
            )
        user_level = ROLE_HIERARCHY.get(ctx.membership.role, 0)
        if user_level < self.minimum_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {self.minimum_role} role or higher",
            )
        return ctx


def require_admin() -> RoleChecker:
    """Require ADMIN role."""
    return RoleChecker("ADMIN")


def require_editor() -> RoleChecker:
    """Require EDITOR role or higher."""
    return RoleChecker("EDITOR")


def require_viewer() -> RoleChecker:
    """Require VIEWER role or higher (any member)."""
    return RoleChecker("VIEWER")


# Legacy compatibility - kept for backwards compatibility
def require_role(minimum_role: str) -> RoleChecker:
    """Create a role checker dependency.

    Usage:
        @router.post("/something")
        async def create_something(
            ctx: Annotated[RequestContext, Depends(require_role("ADMIN"))],
        ):
            ...
    """
    return RoleChecker(minimum_role)
