"""Organization CRUD API routes."""

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.dependencies import get_current_user, require_role
from src.models.organization import Organization, OrganizationMembership
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["organizations"])


class CreateOrganizationRequest(BaseModel):
    name: str
    description: str | None = None
    master_user_id: str | None = None


class UpdateOrganizationRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    master_user_id: str | None = None


class AddOrgMemberRequest(BaseModel):
    user_id: str
    role: str = "MEMBER"


def _org_to_dict(org: Organization, member_count: int | None = None) -> dict[str, Any]:
    return {
        "id": org.id,
        "name": org.name,
        "description": org.description,
        "master_user_id": org.master_user_id,
        "member_count": member_count if member_count is not None else len(org.memberships),
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }


def _org_detail(org: Organization) -> dict[str, Any]:
    d = _org_to_dict(org)
    d["members"] = [
        {
            "user_id": m.user_id,
            "email": m.user.email if m.user else None,
            "full_name": m.user.full_name if m.user else None,
            "role": m.role,
        }
        for m in org.memberships
    ]
    return d


@router.get("/workspaces/{workspace_id}/organizations")
async def list_organizations(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all organizations in a workspace."""
    result = await db.execute(
        select(Organization)
        .where(Organization.workspace_id == workspace_id)
        .options(selectinload(Organization.memberships))
        .order_by(Organization.name)
    )
    orgs = list(result.scalars().all())
    return {"organizations": [_org_to_dict(o) for o in orgs]}


@router.post("/workspaces/{workspace_id}/organizations")
async def create_organization(
    workspace_id: str,
    body: CreateOrganizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Create a new organization (admin only)."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")

    org = Organization(
        id=str(uuid4()),
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        master_user_id=body.master_user_id,
    )
    db.add(org)

    if body.master_user_id:
        membership = OrganizationMembership(
            id=str(uuid4()),
            organization_id=org.id,
            user_id=body.master_user_id,
            role="MASTER",
        )
        db.add(membership)

    await db.commit()
    return _org_to_dict(org, member_count=1 if body.master_user_id else 0)


@router.get("/workspaces/{workspace_id}/organizations/{org_id}")
async def get_organization(
    workspace_id: str,
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get organization detail with members."""
    result = await db.execute(
        select(Organization)
        .where(Organization.id == org_id, Organization.workspace_id == workspace_id)
        .options(
            selectinload(Organization.memberships).selectinload(OrganizationMembership.user)
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _org_detail(org)


@router.patch("/workspaces/{workspace_id}/organizations/{org_id}")
async def update_organization(
    workspace_id: str,
    org_id: str,
    body: UpdateOrganizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Update an organization (admin only)."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id, Organization.workspace_id == workspace_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if body.name is not None:
        org.name = body.name
    if body.description is not None:
        org.description = body.description
    if body.master_user_id is not None:
        org.master_user_id = body.master_user_id

    await db.commit()
    return _org_to_dict(org)


@router.delete("/workspaces/{workspace_id}/organizations/{org_id}")
async def delete_organization(
    workspace_id: str,
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Delete an organization (admin only)."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id, Organization.workspace_id == workspace_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    await db.delete(org)
    await db.commit()
    return {"status": "deleted"}


@router.post("/workspaces/{workspace_id}/organizations/{org_id}/members")
async def add_org_member(
    workspace_id: str,
    org_id: str,
    body: AddOrgMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Add a user to an organization (admin only)."""
    existing = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == body.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already in this organization")

    membership = OrganizationMembership(
        id=str(uuid4()),
        organization_id=org_id,
        user_id=body.user_id,
        role=body.role,
    )
    db.add(membership)
    await db.commit()
    return {"status": "added"}


@router.delete("/workspaces/{workspace_id}/organizations/{org_id}/members/{user_id}")
async def remove_org_member(
    workspace_id: str,
    org_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Remove a user from an organization (admin only)."""
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    await db.delete(membership)
    await db.commit()
    return {"status": "removed"}
