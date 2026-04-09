"""Platform admin authentication dependency.

This module provides authentication dependencies for platform admin operations.
Platform admins can manage the global legal corpus independent of tenants.

Security constraints:
1. User must be authenticated
2. User must have is_platform_admin = true
3. By default, global corpus management is disabled in production
   (controlled by GLOBAL_CORPUS_ENABLED_IN_PROD setting)
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.dependencies.auth import AuthCredentials, get_auth_credentials, get_jwt_payload
from src.models import Tenant, User, WorkspaceMembership
from src.utils.jwt import JWTPayload


@dataclass
class PlatformAdminContext:
    """Context for platform admin operations.

    Contains the authenticated user with platform admin privileges.
    No tenant/workspace context is required for global corpus operations.
    """

    user: User
    tenant: Tenant  # User's home tenant (for audit logging only)


@dataclass
class ScrapingAdminContext:
    """Context for scraping operator access.

    Allows either a platform admin or a workspace admin from the active
    workspace so the scraping console can be tested from a normal admin seat.
    """

    user: User
    tenant: Tenant
    workspace_role: str | None = None


async def get_platform_admin_context(
    auth: Annotated[AuthCredentials, Depends(get_auth_credentials)],
    jwt_payload: Annotated[JWTPayload | None, Depends(get_jwt_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformAdminContext:
    """Get platform admin context for global corpus operations.

    This dependency:
    1. Validates the user is authenticated
    2. Checks that user.is_platform_admin is True
    3. Enforces environment restrictions (disabled in prod by default)

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If not a platform admin or disabled in this environment
    """
    # Environment check - by default disabled in production
    # This can be overridden by setting GLOBAL_CORPUS_ENABLED_IN_PROD=true
    allow_in_prod = getattr(settings, "global_corpus_enabled_in_prod", False)
    if settings.environment == "prod" and not allow_in_prod:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "global_corpus_disabled",
                "message": "Global legal corpus management is disabled in production. "
                "Set GLOBAL_CORPUS_ENABLED_IN_PROD=true to enable.",
            },
        )

    # Load user
    result = await db.execute(
        select(User).where(
            User.id == auth.user_id,
            User.tenant_id == auth.tenant_id,
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

    # Validate token version for session revocation
    if jwt_payload and user.token_version != jwt_payload.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "token_revoked",
                "message": "Your session has been revoked. Please sign in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check platform admin flag
    if not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "platform_admin_required",
                "message": "This operation requires platform administrator privileges.",
            },
        )

    # Load tenant (for audit logging purposes)
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return PlatformAdminContext(user=user, tenant=tenant)


def require_platform_admin():
    """Dependency factory for requiring platform admin access.

    Usage:
        @router.post("/global/legal-instruments")
        async def create_instrument(
            ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
        ):
            ...
    """
    return get_platform_admin_context


async def get_platform_admin_operator_context(
    auth: Annotated[AuthCredentials, Depends(get_auth_credentials)],
    jwt_payload: Annotated[JWTPayload | None, Depends(get_jwt_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformAdminContext:
    """Platform admin without global-corpus production gate (operator / tenant bootstrap)."""
    result = await db.execute(
        select(User).where(
            User.id == auth.user_id,
            User.tenant_id == auth.tenant_id,
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

    if jwt_payload and user.token_version != jwt_payload.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "token_revoked",
                "message": "Your session has been revoked. Please sign in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "platform_admin_required",
                "message": "This operation requires platform administrator privileges.",
            },
        )

    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return PlatformAdminContext(user=user, tenant=tenant)


def require_platform_admin_operator():
    """Platform admin dependency for operator routes (not blocked by corpus prod flag)."""
    return get_platform_admin_operator_context


async def get_scraping_admin_operator_context(
    auth: Annotated[AuthCredentials, Depends(get_auth_credentials)],
    jwt_payload: Annotated[JWTPayload | None, Depends(get_jwt_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScrapingAdminContext:
    """Allow scraping access for platform admins or current-workspace admins."""
    result = await db.execute(
        select(User).where(
            User.id == auth.user_id,
            User.tenant_id == auth.tenant_id,
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

    if jwt_payload and user.token_version != jwt_payload.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "token_revoked",
                "message": "Your session has been revoked. Please sign in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if user.is_platform_admin:
        return ScrapingAdminContext(user=user, tenant=tenant, workspace_role=None)

    if auth.workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "workspace_admin_required",
                "message": "This operation requires workspace administrator privileges.",
            },
        )

    membership_result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.tenant_id == auth.tenant_id,
            WorkspaceMembership.workspace_id == auth.workspace_id,
            WorkspaceMembership.user_id == auth.user_id,
        )
    )
    membership = membership_result.scalar_one_or_none()

    if membership is None or membership.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "workspace_admin_required",
                "message": "This operation requires workspace administrator privileges.",
            },
        )

    return ScrapingAdminContext(
        user=user,
        tenant=tenant,
        workspace_role=membership.role,
    )


def require_scraping_admin_operator():
    """Scraping operator dependency for platform admins or workspace admins."""
    return get_scraping_admin_operator_context


async def require_dev_or_platform_admin_for_tenant_create(
    jwt_payload: Annotated[JWTPayload | None, Depends(get_jwt_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Allow unauthenticated tenant bootstrap only in dev; otherwise platform admin."""
    if settings.environment == "dev":
        return
    if jwt_payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "platform_admin_required",
                "message": "Creating organisations requires platform administrator sign-in.",
            },
        )
    result = await db.execute(
        select(User).where(
            User.id == jwt_payload.sub,
            User.tenant_id == jwt_payload.tenant_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "platform_admin_required",
                "message": "Creating organisations requires platform administrator privileges.",
            },
        )
