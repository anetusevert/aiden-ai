"""Workspace-scoped routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import (
    RequestContext,
    get_workspace_context,
    require_admin,
    require_viewer,
)
from src.schemas import (
    MemberInviteRequest,
    MemberRoleUpdateRequest,
    MemberWithUserResponse,
    WorkspaceMembershipCreate,
    WorkspaceMembershipResponse,
)
from src.services import (
    DuplicateMembershipError,
    LastAdminError,
    MembershipNotFoundError,
    UserNotFoundError,
    WorkspaceMembershipService,
    log_audit_event,
)
from src.services.workspace_membership_service import (
    CrossTenantEmailError,
    InitialPasswordRequiredError,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post(
    "/{workspace_id}/memberships",
    response_model=WorkspaceMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to workspace",
    description="Add a user to a workspace with a specific role. Requires ADMIN role.",
)
async def create_membership(
    data: WorkspaceMembershipCreate,
    workspace_id: Annotated[str, Path(description="Workspace ID")],
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceMembershipResponse:
    """Add a user to a workspace.
    
    Requires:
    - X-Tenant-Id header
    - X-Workspace-Id header matching workspace_id in path
    - X-User-Id header for a user who is ADMIN in the workspace
    """
    # Verify path workspace_id matches context workspace
    if ctx.workspace is None or workspace_id != ctx.workspace.id:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="membership.create",
            status="fail",
            resource_type="membership",
            meta={"reason": "workspace_mismatch"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace ID in path does not match X-Workspace-Id header",
        )
    
    service = WorkspaceMembershipService(db)
    try:
        new_membership = await service.create_membership(ctx.workspace, data)
        
        # Log successful membership creation
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="membership.create",
            status="success",
            resource_type="membership",
            resource_id=new_membership.id,
            meta={"target_user_id": data.user_id, "role": data.role},
            request=request,
        )
        
        return WorkspaceMembershipResponse.model_validate(new_membership)
    except UserNotFoundError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="membership.create",
            status="fail",
            resource_type="membership",
            meta={"reason": "user_not_found", "target_user_id": data.user_id},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DuplicateMembershipError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="membership.create",
            status="fail",
            resource_type="membership",
            meta={"reason": "duplicate", "target_user_id": data.user_id},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/{workspace_id}/memberships",
    response_model=list[WorkspaceMembershipResponse],
    summary="List workspace members",
    description="List all members of a workspace. Any member can view.",
)
async def list_memberships(
    workspace_id: Annotated[str, Path(description="Workspace ID")],
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkspaceMembershipResponse]:
    """List all members of a workspace.
    
    Requires X-Tenant-Id, X-Workspace-Id, and X-User-Id headers.
    Any workspace member can view the membership list.
    """
    # Verify path workspace_id matches context workspace
    if ctx.workspace is None or workspace_id != ctx.workspace.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace ID in path does not match X-Workspace-Id header",
        )
    
    service = WorkspaceMembershipService(db)
    memberships = await service.list_memberships(workspace_id, ctx.tenant.id)
    return [WorkspaceMembershipResponse.model_validate(m) for m in memberships]


# =============================================================================
# Member Management Endpoints (V2 - with user details)
# =============================================================================


@router.get(
    "/{workspace_id}/members",
    response_model=list[MemberWithUserResponse],
    summary="List workspace members with details",
    description="List all members with user details. Requires VIEWER+ role.",
)
async def list_members(
    workspace_id: Annotated[str, Path(description="Workspace ID")],
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MemberWithUserResponse]:
    """List all members of a workspace with user details.
    
    Returns membership info plus email, full_name, is_active for each member.
    Any workspace member can view (transparency).
    """
    # Verify path workspace_id matches context workspace
    if ctx.workspace is None or workspace_id != ctx.workspace.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace ID in path does not match context",
        )
    
    service = WorkspaceMembershipService(db)
    memberships = await service.list_memberships_with_users(
        workspace_id, ctx.tenant.id
    )
    return [MemberWithUserResponse.from_membership(m) for m in memberships]


@router.post(
    "/{workspace_id}/members",
    response_model=MemberWithUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite/add member by email",
    description="Add a member by email. Creates user if not exists. Requires ADMIN.",
)
async def invite_member(
    data: MemberInviteRequest,
    workspace_id: Annotated[str, Path(description="Workspace ID")],
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemberWithUserResponse:
    """Invite a member to the workspace by email.
    
    If the user already exists in the tenant, they are added to the workspace.
    If not, a new user is created in the tenant (dev "invite" - no email sent).
    
    Requires ADMIN role.
    """
    # Verify path workspace_id matches context workspace
    if ctx.workspace is None or workspace_id != ctx.workspace.id:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.add",
            status="fail",
            resource_type="membership",
            meta={"reason": "workspace_mismatch", "email": data.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace ID in path does not match context",
        )
    
    service = WorkspaceMembershipService(db)
    try:
        membership, user, user_created = await service.invite_member_by_email(
            workspace=ctx.workspace,
            email=data.email,
            role=data.role,
            full_name=data.full_name,
            initial_password=data.initial_password,
        )
        
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.add",
            status="success",
            resource_type="membership",
            resource_id=membership.id,
            meta={
                "email": data.email,
                "role": data.role,
                "user_created": user_created,
            },
            request=request,
        )
        
        return MemberWithUserResponse.from_membership(membership)

    except InitialPasswordRequiredError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.add",
            status="fail",
            resource_type="membership",
            meta={"reason": "initial_password_required", "email": data.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except CrossTenantEmailError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.add",
            status="fail",
            resource_type="membership",
            meta={"reason": "cross_tenant_email", "email": data.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    except DuplicateMembershipError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.add",
            status="fail",
            resource_type="membership",
            meta={"reason": "duplicate", "email": data.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.patch(
    "/{workspace_id}/members/{membership_id}",
    response_model=MemberWithUserResponse,
    summary="Update member role",
    description="Change a member's role. Requires ADMIN. Cannot demote last admin.",
)
async def update_member_role(
    data: MemberRoleUpdateRequest,
    workspace_id: Annotated[str, Path(description="Workspace ID")],
    membership_id: Annotated[str, Path(description="Membership ID")],
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemberWithUserResponse:
    """Update a member's role in the workspace.
    
    Requires ADMIN role.
    Cannot demote the last admin - at least one admin must remain.
    """
    # Verify path workspace_id matches context workspace
    if ctx.workspace is None or workspace_id != ctx.workspace.id:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.role.update",
            status="fail",
            resource_type="membership",
            resource_id=membership_id,
            meta={"reason": "workspace_mismatch"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace ID in path does not match context",
        )
    
    service = WorkspaceMembershipService(db)
    
    # Get existing membership for audit log
    existing = await service.get_membership_by_id(
        membership_id, workspace_id, ctx.tenant.id
    )
    old_role = existing.role if existing else None
    
    try:
        membership = await service.update_membership_role(
            membership_id=membership_id,
            workspace_id=workspace_id,
            tenant_id=ctx.tenant.id,
            new_role=data.role,
        )
        
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.role.update",
            status="success",
            resource_type="membership",
            resource_id=membership_id,
            meta={
                "old_role": old_role,
                "new_role": data.role,
                "target_user_id": membership.user_id,
            },
            request=request,
        )
        
        return MemberWithUserResponse.from_membership(membership)
        
    except MembershipNotFoundError:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.role.update",
            status="fail",
            resource_type="membership",
            resource_id=membership_id,
            meta={"reason": "not_found"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )
    except LastAdminError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.role.update",
            status="fail",
            resource_type="membership",
            resource_id=membership_id,
            meta={"reason": "last_admin"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{workspace_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove member from workspace",
    description="Remove a member from the workspace. Requires ADMIN. Cannot remove last admin.",
)
async def remove_member(
    workspace_id: Annotated[str, Path(description="Workspace ID")],
    membership_id: Annotated[str, Path(description="Membership ID")],
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a member from the workspace.
    
    Requires ADMIN role.
    Cannot remove the last admin - at least one admin must remain.
    """
    # Verify path workspace_id matches context workspace
    if ctx.workspace is None or workspace_id != ctx.workspace.id:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.remove",
            status="fail",
            resource_type="membership",
            resource_id=membership_id,
            meta={"reason": "workspace_mismatch"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace ID in path does not match context",
        )
    
    service = WorkspaceMembershipService(db)
    try:
        membership = await service.remove_membership(
            membership_id=membership_id,
            workspace_id=workspace_id,
            tenant_id=ctx.tenant.id,
        )
        
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.remove",
            status="success",
            resource_type="membership",
            resource_id=membership_id,
            meta={
                "removed_user_id": membership.user_id,
                "removed_role": membership.role,
            },
            request=request,
        )
        
    except MembershipNotFoundError:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.remove",
            status="fail",
            resource_type="membership",
            resource_id=membership_id,
            meta={"reason": "not_found"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )
    except LastAdminError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.member.remove",
            status="fail",
            resource_type="membership",
            resource_id=membership_id,
            meta={"reason": "last_admin"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
