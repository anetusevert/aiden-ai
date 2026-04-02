"""Audit log router for viewing audit trails.

This router provides read-only access to audit logs for administrators.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import RequestContext, get_workspace_context
from src.models.audit_log import AuditLog
from src.models.workspace import Workspace
from src.schemas.audit import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List audit logs",
    description="""
    List audit log entries for the current tenant.
    
    **Access Control**: Requires ADMIN role in the current workspace context.
    
    The returned logs are scoped to the tenant from the authentication context.
    If workspace_id is specified, logs are further filtered to that workspace.
    """,
    responses={
        200: {"description": "List of audit log entries"},
        401: {"description": "Not authenticated"},
        403: {"description": "Requires ADMIN role"},
    },
)
async def list_audit_logs(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[
        str | None,
        Query(description="Filter by workspace ID (must belong to tenant)"),
    ] = None,
    action: Annotated[
        str | None,
        Query(description="Filter by action (e.g., 'tenant.create')"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=200, description="Maximum number of entries to return"),
    ] = 50,
) -> AuditLogListResponse:
    """List audit logs for the tenant.

    Requires:
    - Valid authentication (JWT or headers)
    - ADMIN role in the current workspace

    Returns:
    - Audit logs scoped to the authenticated tenant
    - Optionally filtered by workspace_id and action
    - Ordered by created_at descending (most recent first)
    """
    # Check for ADMIN role
    if not ctx.has_role("ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires ADMIN role to view audit logs",
        )

    # Validate workspace_id belongs to tenant if specified
    if workspace_id:
        workspace_result = await db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.tenant_id == ctx.tenant.id,
            )
        )
        if workspace_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace not found or does not belong to tenant",
            )

    # Build query - always scoped to tenant
    query = select(AuditLog).where(AuditLog.tenant_id == ctx.tenant.id)

    # Apply filters
    if workspace_id:
        query = query.where(AuditLog.workspace_id == workspace_id)
    if action:
        query = query.where(AuditLog.action == action)

    # Get total count
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order by most recent first, apply limit
    query = query.order_by(AuditLog.created_at.desc()).limit(limit)

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        limit=limit,
    )
