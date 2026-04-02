"""Tenant, workspace, and user routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import (
    RequestContext,
    get_tenant_context,
    require_admin,
)
from src.dependencies.platform_admin import require_dev_or_platform_admin_for_tenant_create
from src.schemas import (
    BootstrapResponse,
    TenantCreateWithBootstrap,
    TenantResponse,
    UserCreate,
    UserResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)
from src.services import BootstrapService, UserService, WorkspaceService, log_audit_event
from src.services.bootstrap_service import TenantExistsError
from src.services.user_service import DuplicateUserError
from src.services.workspace_service import DuplicateWorkspaceError

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "",
    response_model=BootstrapResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant",
    description="""
    Create a new tenant (organization) in the system.
    
    **Bootstrap Mode**: Optionally include a `bootstrap` payload to create:
    - First workspace
    - First admin user
    - ADMIN membership linking user to workspace
    
    This allows bootstrapping a tenant without needing any prior database seeding.
    
    **Development Note**: This endpoint is open for development purposes.
    In production, tenant creation would be restricted to system administrators.
    """,
)
async def create_tenant(
    data: TenantCreateWithBootstrap,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_dev_or_platform_admin_for_tenant_create)],
) -> BootstrapResponse:
    """Create a new tenant with optional bootstrap.
    
    This endpoint is open for development. In production, this would be
    restricted to system administrators or a separate admin API.
    
    If bootstrap payload is provided, creates tenant + workspace + admin user +
    membership in a single atomic transaction.
    """
    service = BootstrapService(db)
    try:
        result = await service.create_tenant_with_bootstrap(data)
        
        # Log successful tenant creation
        await log_audit_event(
            db=db,
            ctx=None,
            action="tenant.create",
            status="success",
            tenant_id=result.tenant_id,
            workspace_id=result.workspace_id,
            user_id=result.admin_user_id,
            resource_type="tenant",
            resource_id=result.tenant_id,
            meta={
                "tenant_name": result.tenant_name,
                "bootstrapped": data.bootstrap is not None,
            },
            request=request,
        )
        
        return result
    except TenantExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/{tenant_id}/workspaces",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
    description="Create a new workspace within a tenant. Requires ADMIN role.",
)
async def create_workspace(
    data: WorkspaceCreate,
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceResponse:
    """Create a workspace within a tenant.
    
    Requires:
    - X-Tenant-Id header matching the tenant_id in path
    - X-Workspace-Id header for an existing workspace where user is ADMIN
    - X-User-Id header identifying the user
    """
    # Verify path tenant_id matches context tenant
    if tenant_id != ctx.tenant.id:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.create",
            status="fail",
            resource_type="workspace",
            meta={"reason": "tenant_mismatch"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID in path does not match X-Tenant-Id header",
        )
    
    service = WorkspaceService(db)
    try:
        workspace = await service.create_workspace(tenant_id, data)
        
        # Log successful workspace creation
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.create",
            status="success",
            resource_type="workspace",
            resource_id=workspace.id,
            meta={"workspace_name": workspace.name},
            request=request,
        )
        
        return WorkspaceResponse.model_validate(workspace)
    except DuplicateWorkspaceError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.create",
            status="fail",
            resource_type="workspace",
            meta={"reason": "duplicate", "workspace_name": data.name},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/{tenant_id}/workspaces",
    response_model=list[WorkspaceResponse],
    summary="List workspaces",
    description="List all workspaces in a tenant. Requires valid tenant + user headers.",
)
async def list_workspaces(
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    ctx: Annotated[RequestContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkspaceResponse]:
    """List all workspaces for the tenant.
    
    Requires X-Tenant-Id and X-User-Id headers.
    User must belong to the tenant.
    """
    # Verify path matches context tenant
    if tenant_id != ctx.tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID in path does not match X-Tenant-Id header",
        )
    
    service = WorkspaceService(db)
    workspaces = await service.list_workspaces(tenant_id)
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post(
    "/{tenant_id}/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user within a tenant. Requires ADMIN role.",
)
async def create_user(
    data: UserCreate,
    tenant_id: Annotated[str, Path(description="Tenant ID")],
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Create a user within a tenant.
    
    Requires:
    - X-Tenant-Id header matching the tenant_id in path
    - X-Workspace-Id header for an existing workspace where user is ADMIN
    - X-User-Id header identifying the user
    """
    # Verify path tenant_id matches context tenant
    if tenant_id != ctx.tenant.id:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="user.create",
            status="fail",
            resource_type="user",
            meta={"reason": "tenant_mismatch"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID in path does not match X-Tenant-Id header",
        )
    
    service = UserService(db)
    try:
        user = await service.create_user(tenant_id, data)
        
        # Log successful user creation
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="user.create",
            status="success",
            resource_type="user",
            resource_id=user.id,
            meta={"email": user.email},
            request=request,
        )
        
        return UserResponse.model_validate(user)
    except DuplicateUserError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="user.create",
            status="fail",
            resource_type="user",
            meta={"reason": "duplicate", "email": data.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
