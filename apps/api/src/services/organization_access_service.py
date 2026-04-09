"""Helpers for resolving and healing organization access within a workspace."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization, OrganizationMembership


def _org_role_for_workspace_role(
    workspace_role: str,
    *,
    is_master: bool = False,
) -> str:
    if is_master:
        return "MASTER"
    if workspace_role == "ADMIN":
        return "ADMIN"
    return "MEMBER"


async def ensure_workspace_org_access(
    db: AsyncSession,
    *,
    tenant_id: str,
    workspace_id: str,
    workspace_name: str | None,
    user_id: str,
    workspace_role: str,
) -> str | None:
    """Return an accessible organization ID for the user within the workspace.

    This function self-heals common bootstrap gaps:
    - bootstrapped admins with a workspace membership but no organization
    - invited members in a single-organization workspace who were never added to
      that organization

    To avoid assigning users to the wrong organization in multi-org workspaces,
    auto-enrollment only happens when there is exactly one organization in the
    workspace or when an admin needs the first default organization created.
    """
    membership_stmt = (
        select(OrganizationMembership.organization_id)
        .join(
            Organization,
            Organization.id == OrganizationMembership.organization_id,
        )
        .where(
            Organization.workspace_id == workspace_id,
            OrganizationMembership.user_id == user_id,
        )
        .order_by(OrganizationMembership.created_at.asc())
        .limit(1)
    )
    org_id = (await db.execute(membership_stmt)).scalar_one_or_none()
    if org_id:
        return org_id

    master_stmt = (
        select(Organization)
        .where(
            Organization.workspace_id == workspace_id,
            Organization.master_user_id == user_id,
        )
        .order_by(Organization.created_at.asc())
        .limit(1)
    )
    master_org = (await db.execute(master_stmt)).scalar_one_or_none()
    if master_org is not None:
        db.add(
            OrganizationMembership(
                organization_id=master_org.id,
                user_id=user_id,
                role="MASTER",
            )
        )
        await db.commit()
        return master_org.id

    orgs_stmt = (
        select(Organization)
        .where(Organization.workspace_id == workspace_id)
        .order_by(Organization.created_at.asc())
        .limit(2)
    )
    orgs = list((await db.execute(orgs_stmt)).scalars().all())

    if not orgs:
        if workspace_role != "ADMIN":
            return None

        org = Organization(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            name=(workspace_name or "Default").strip() or "Default",
            description="Auto-created default organization",
            master_user_id=user_id,
        )
        db.add(org)
        await db.flush()
        db.add(
            OrganizationMembership(
                organization_id=org.id,
                user_id=user_id,
                role="MASTER",
            )
        )
        await db.commit()
        return org.id

    if len(orgs) == 1:
        org = orgs[0]
        is_master = workspace_role == "ADMIN" and (
            org.master_user_id is None or org.master_user_id == user_id
        )
        if is_master and org.master_user_id is None:
            org.master_user_id = user_id

        db.add(
            OrganizationMembership(
                organization_id=org.id,
                user_id=user_id,
                role=_org_role_for_workspace_role(
                    workspace_role,
                    is_master=is_master,
                ),
            )
        )
        await db.commit()
        return org.id

    return None
