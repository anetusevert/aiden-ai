"""Resolve workspace + membership for password login."""

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Workspace, WorkspaceMembership


async def resolve_workspace_for_login(
    db: AsyncSession,
    user: User,
) -> tuple[Workspace, WorkspaceMembership] | None:
    """Pick workspace for JWT: default_workspace_id if valid, else best membership."""
    if user.default_workspace_id:
        ws_result = await db.execute(
            select(Workspace).where(
                Workspace.id == user.default_workspace_id,
                Workspace.tenant_id == user.tenant_id,
            )
        )
        workspace = ws_result.scalar_one_or_none()
        if workspace:
            mem_result = await db.execute(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace.id,
                    WorkspaceMembership.user_id == user.id,
                )
            )
            membership = mem_result.scalar_one_or_none()
            if membership:
                return workspace, membership

    stmt = (
        select(Workspace, WorkspaceMembership)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Workspace.id,
        )
        .where(
            WorkspaceMembership.user_id == user.id,
            Workspace.tenant_id == user.tenant_id,
        )
        .order_by(
            case((WorkspaceMembership.role == "ADMIN", 0), else_=1),
            WorkspaceMembership.created_at,
        )
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None
    workspace, membership = row[0], row[1]
    return workspace, membership
