"""Platform admin bootstrap service.

This module provides a one-time bootstrap mechanism for designating platform admins
without requiring direct database access.

Security constraints:
1. Only runs in dev/staging environments by default
2. In production, requires GLOBAL_CORPUS_ENABLED_IN_PROD=true
3. Requires existing user (does NOT auto-create users)
4. All bootstrap actions are logged

Usage:
1. Set PLATFORM_ADMIN_EMAIL=admin@example.com in environment
2. On application startup, if user exists, is_platform_admin is set to true
3. If user doesn't exist, a warning is logged

This removes the need for manual SQL: UPDATE users SET is_platform_admin=true...
"""

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models import User
from src.utils.passwords import normalize_email

logger = logging.getLogger(__name__)


class PlatformAdminBootstrapError(Exception):
    """Raised when platform admin bootstrap fails."""

    pass


async def bootstrap_platform_admin(db: AsyncSession) -> dict[str, Any]:
    """Bootstrap platform admin from PLATFORM_ADMIN_EMAIL environment variable.

    This function:
    1. Checks if bootstrap is allowed in current environment
    2. Looks up user by email
    3. Sets is_platform_admin=true if user exists
    4. Logs all actions

    Args:
        db: Async database session

    Returns:
        dict with bootstrap result:
        - action: "skipped" | "set" | "already_admin" | "user_not_found" | "blocked"
        - email: The email address processed (or None)
        - message: Human-readable status message

    Raises:
        PlatformAdminBootstrapError: If bootstrap fails unexpectedly
    """
    result: dict[str, Any] = {
        "action": "skipped",
        "email": None,
        "message": "No platform admin email configured",
    }

    # Check if PLATFORM_ADMIN_EMAIL is set
    admin_email = settings.platform_admin_email
    if not admin_email:
        logger.debug("Platform admin bootstrap: No PLATFORM_ADMIN_EMAIL configured, skipping")
        return result

    result["email"] = admin_email

    # Environment safety check
    # In production, bootstrap is blocked unless GLOBAL_CORPUS_ENABLED_IN_PROD=true
    if settings.environment == "prod":
        if not settings.global_corpus_enabled_in_prod:
            result["action"] = "blocked"
            result["message"] = (
                f"Platform admin bootstrap blocked in production. "
                f"PLATFORM_ADMIN_EMAIL={admin_email} was set but "
                f"GLOBAL_CORPUS_ENABLED_IN_PROD=false. "
                f"Set GLOBAL_CORPUS_ENABLED_IN_PROD=true to enable bootstrap in production."
            )
            logger.warning(
                "PLATFORM_ADMIN_BOOTSTRAP_BLOCKED",
                extra={
                    "email": admin_email,
                    "environment": settings.environment,
                    "reason": "global_corpus_not_enabled_in_prod",
                },
            )
            return result

    # Look up user by email
    stmt = select(User).where(User.email_normalized == normalize_email(admin_email))
    db_result = await db.execute(stmt)
    user = db_result.scalar_one_or_none()

    if not user:
        result["action"] = "user_not_found"
        result["message"] = (
            f"Platform admin bootstrap: User with email '{admin_email}' not found. "
            f"Create the user first, then restart the application."
        )
        logger.warning(
            "PLATFORM_ADMIN_BOOTSTRAP_USER_NOT_FOUND",
            extra={
                "email": admin_email,
                "environment": settings.environment,
                "action": "user_not_found",
            },
        )
        return result

    # Check if already admin
    if user.is_platform_admin:
        result["action"] = "already_admin"
        result["message"] = (
            f"Platform admin bootstrap: User '{admin_email}' is already a platform admin. "
            f"No changes made."
        )
        logger.info(
            "PLATFORM_ADMIN_BOOTSTRAP_ALREADY_ADMIN",
            extra={
                "email": admin_email,
                "user_id": user.id,
                "environment": settings.environment,
            },
        )
        return result

    # Set is_platform_admin = true
    try:
        user.is_platform_admin = True
        await db.commit()
        await db.refresh(user)

        result["action"] = "set"
        result["message"] = (
            f"Platform admin bootstrap: Successfully set is_platform_admin=true "
            f"for user '{admin_email}' (user_id={user.id})"
        )
        logger.info(
            "PLATFORM_ADMIN_BOOTSTRAP_SUCCESS",
            extra={
                "email": admin_email,
                "user_id": user.id,
                "tenant_id": user.tenant_id,
                "environment": settings.environment,
                "action": "set",
            },
        )
        return result

    except Exception as e:
        await db.rollback()
        logger.error(
            "PLATFORM_ADMIN_BOOTSTRAP_FAILED",
            extra={
                "email": admin_email,
                "environment": settings.environment,
                "error": str(e),
            },
            exc_info=True,
        )
        raise PlatformAdminBootstrapError(
            f"Failed to set platform admin for '{admin_email}': {e}"
        ) from e


async def revoke_platform_admin(db: AsyncSession, email: str) -> dict[str, Any]:
    """Revoke platform admin privileges from a user.

    This is the inverse of bootstrap - used for rotating platform admins.

    Args:
        db: Async database session
        email: Email of user to revoke admin from

    Returns:
        dict with revoke result:
        - action: "revoked" | "not_admin" | "user_not_found"
        - email: The email address processed
        - message: Human-readable status message
    """
    result: dict[str, Any] = {
        "action": "user_not_found",
        "email": email,
        "message": f"User with email '{email}' not found",
    }

    # Look up user by email
    stmt = select(User).where(User.email_normalized == normalize_email(email))
    db_result = await db.execute(stmt)
    user = db_result.scalar_one_or_none()

    if not user:
        logger.warning(
            "PLATFORM_ADMIN_REVOKE_USER_NOT_FOUND",
            extra={"email": email},
        )
        return result

    if not user.is_platform_admin:
        result["action"] = "not_admin"
        result["message"] = f"User '{email}' is not a platform admin. No changes made."
        logger.info(
            "PLATFORM_ADMIN_REVOKE_NOT_ADMIN",
            extra={"email": email, "user_id": user.id},
        )
        return result

    # Revoke admin
    user.is_platform_admin = False
    await db.commit()
    await db.refresh(user)

    result["action"] = "revoked"
    result["message"] = f"Successfully revoked platform admin from '{email}' (user_id={user.id})"
    logger.info(
        "PLATFORM_ADMIN_REVOKE_SUCCESS",
        extra={
            "email": email,
            "user_id": user.id,
            "tenant_id": user.tenant_id,
        },
    )
    return result
