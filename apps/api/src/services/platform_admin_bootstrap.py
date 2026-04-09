"""Platform admin bootstrap service.

This module enforces a configured super-admin email on startup.

Behavior:
1. Looks up the configured email
2. Makes that user the sole platform admin
3. Ensures that user is ADMIN in every workspace in their tenant
4. Demotes other tenant workspace admins to EDITOR
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models import User, Workspace, WorkspaceMembership
from src.utils.passwords import normalize_email

logger = logging.getLogger(__name__)


class PlatformAdminBootstrapError(Exception):
    """Raised when platform admin bootstrap fails."""

    pass


async def bootstrap_platform_admin(db: AsyncSession) -> dict[str, Any]:
    """Enforce the configured platform admin email as the tenant super admin.

    This function:
    1. Looks up the configured user by email
    2. Revokes platform-admin from every other user
    3. Ensures the configured user is ADMIN in every workspace in their tenant
    4. Demotes every other ADMIN membership in that tenant to EDITOR

    Args:
        db: Async database session

    Returns:
        dict with bootstrap result:
        - action: "skipped" | "enforced" | "user_not_found"
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

    admin_email = settings.platform_admin_email
    if not admin_email:
        logger.debug("Platform admin bootstrap: No PLATFORM_ADMIN_EMAIL configured, skipping")
        return result

    result["email"] = admin_email

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

    try:
        other_platform_admins = (
            await db.execute(
                select(User).where(
                    User.id != user.id,
                    User.is_platform_admin.is_(True),
                )
            )
        ).scalars().all()
        for other_user in other_platform_admins:
            other_user.is_platform_admin = False

        user.is_platform_admin = True
        workspaces = (
            await db.execute(
                select(Workspace).where(Workspace.tenant_id == user.tenant_id)
            )
        ).scalars().all()
        memberships = (
            await db.execute(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.tenant_id == user.tenant_id
                )
            )
        ).scalars().all()

        membership_by_workspace = {
            membership.workspace_id: membership
            for membership in memberships
            if membership.user_id == user.id
        }

        promoted_workspaces = 0
        created_memberships = 0
        demoted_admins = 0

        for workspace in workspaces:
            own_membership = membership_by_workspace.get(workspace.id)
            if own_membership is None:
                own_membership = WorkspaceMembership(
                    tenant_id=user.tenant_id,
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role="ADMIN",
                )
                db.add(own_membership)
                membership_by_workspace[workspace.id] = own_membership
                created_memberships += 1
            elif own_membership.role != "ADMIN":
                own_membership.role = "ADMIN"
                promoted_workspaces += 1

            for membership in memberships:
                if (
                    membership.workspace_id == workspace.id
                    and membership.user_id != user.id
                    and membership.role == "ADMIN"
                ):
                    membership.role = "EDITOR"
                    demoted_admins += 1

        if user.default_workspace_id is None and workspaces:
            user.default_workspace_id = workspaces[0].id

        await db.commit()
        await db.refresh(user)

        result["action"] = "enforced"
        result["message"] = (
            f"Platform admin bootstrap: enforced '{admin_email}' as sole platform admin "
            f"and tenant super admin (created_memberships={created_memberships}, "
            f"promoted_workspaces={promoted_workspaces}, demoted_admins={demoted_admins}, "
            f"revoked_platform_admins={len(other_platform_admins)})"
        )
        result["created_memberships"] = created_memberships
        result["promoted_workspaces"] = promoted_workspaces
        result["demoted_admins"] = demoted_admins
        result["revoked_platform_admins"] = len(other_platform_admins)
        logger.info(
            "PLATFORM_ADMIN_BOOTSTRAP_SUCCESS",
            extra={
                "email": admin_email,
                "user_id": user.id,
                "tenant_id": user.tenant_id,
                "environment": settings.environment,
                "action": "enforced",
                "created_memberships": created_memberships,
                "promoted_workspaces": promoted_workspaces,
                "demoted_admins": demoted_admins,
                "revoked_platform_admins": len(other_platform_admins),
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
