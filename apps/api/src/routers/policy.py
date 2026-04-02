"""Policy management routes (Admin only).

All endpoints in this router require ADMIN role.
Policy profiles are tenant-scoped.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, get_workspace_context, require_admin
from src.schemas.policy import (
    AttachPolicyRequest,
    PolicyProfileCreate,
    PolicyProfileResponse,
    PolicyProfileUpdate,
    PolicyResolveResponse,
)
from src.schemas.workspace import WorkspaceResponse
from src.services import log_audit_event
from src.services.policy_service import (
    PolicyProfileNameExistsError,
    PolicyProfileNotFoundError,
    PolicyProfileNotInTenantError,
    PolicyService,
    WorkspaceNotFoundError,
)

router = APIRouter(prefix="/policy-profiles", tags=["policy"])

# Separate router for workspace policy attachment
workspace_policy_router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# Separate router for policy resolution
policy_resolve_router = APIRouter(prefix="/policy", tags=["policy"])


# =============================================================================
# Policy Profile CRUD (Admin only)
# =============================================================================


@router.post(
    "",
    response_model=PolicyProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a policy profile",
    description="Create a new policy profile for the tenant. Requires ADMIN role.",
)
async def create_policy_profile(
    data: PolicyProfileCreate,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyProfileResponse:
    """Create a new policy profile.

    Only ADMINs can create policy profiles. The profile is automatically
    scoped to the authenticated tenant.
    """
    service = PolicyService(db)
    try:
        profile = await service.create_policy_profile(ctx.tenant.id, data)

        # Audit log
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="policy_profile.create",
            status="success",
            resource_type="policy_profile",
            resource_id=profile.id,
            meta={
                "policy_name": profile.name,
                "is_default": profile.is_default,
            },
            request=request,
        )

        return PolicyProfileResponse.model_validate(profile)
    except PolicyProfileNameExistsError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="policy_profile.create",
            status="fail",
            resource_type="policy_profile",
            meta={"reason": "duplicate_name", "policy_name": data.name},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "",
    response_model=list[PolicyProfileResponse],
    summary="List policy profiles",
    description="List all policy profiles for the tenant. Requires ADMIN role.",
)
async def list_policy_profiles(
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyProfileResponse]:
    """List all policy profiles for the tenant."""
    service = PolicyService(db)
    profiles = await service.list_policy_profiles(ctx.tenant.id)
    return [PolicyProfileResponse.model_validate(p) for p in profiles]


@router.patch(
    "/{policy_id}",
    response_model=PolicyProfileResponse,
    summary="Update a policy profile",
    description="Update an existing policy profile. Requires ADMIN role.",
)
async def update_policy_profile(
    policy_id: Annotated[str, Path(description="Policy profile ID")],
    data: PolicyProfileUpdate,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyProfileResponse:
    """Update a policy profile.

    Only ADMINs can update policy profiles. Partial updates are supported.
    """
    service = PolicyService(db)
    try:
        profile = await service.update_policy_profile(ctx.tenant.id, policy_id, data)

        # Build meta with only changed fields
        meta: dict[str, object] = {"policy_id": policy_id, "policy_name": profile.name}
        if data.name is not None:
            meta["updated_name"] = data.name
        if data.is_default is not None:
            meta["updated_is_default"] = data.is_default
        if data.config is not None:
            meta["config_updated"] = True

        await log_audit_event(
            db=db,
            ctx=ctx,
            action="policy_profile.update",
            status="success",
            resource_type="policy_profile",
            resource_id=policy_id,
            meta=meta,
            request=request,
        )

        return PolicyProfileResponse.model_validate(profile)
    except PolicyProfileNotFoundError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="policy_profile.update",
            status="fail",
            resource_type="policy_profile",
            resource_id=policy_id,
            meta={"reason": "not_found"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PolicyProfileNameExistsError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="policy_profile.update",
            status="fail",
            resource_type="policy_profile",
            resource_id=policy_id,
            meta={"reason": "duplicate_name", "attempted_name": data.name},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


# =============================================================================
# Workspace Policy Attachment (Admin only)
# =============================================================================


@workspace_policy_router.post(
    "/{workspace_id}/policy-profile",
    response_model=WorkspaceResponse,
    summary="Attach policy profile to workspace",
    description="Attach a policy profile to a workspace. Requires ADMIN role.",
)
async def attach_policy_to_workspace(
    workspace_id: Annotated[str, Path(description="Workspace ID")],
    data: AttachPolicyRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceResponse:
    """Attach a policy profile to a workspace.

    The policy profile must belong to the same tenant as the workspace.
    Only ADMINs can attach policy profiles.
    """
    # Verify workspace matches context workspace
    if ctx.workspace is None or workspace_id != ctx.workspace.id:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.policy_profile.attach",
            status="fail",
            resource_type="workspace",
            resource_id=workspace_id,
            meta={"reason": "workspace_mismatch"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace ID in path does not match X-Workspace-Id header",
        )

    service = PolicyService(db)
    try:
        workspace = await service.attach_policy_to_workspace(
            tenant_id=ctx.tenant.id,
            workspace_id=workspace_id,
            policy_profile_id=data.policy_profile_id,
        )

        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.policy_profile.attach",
            status="success",
            resource_type="workspace",
            resource_id=workspace_id,
            meta={
                "policy_profile_id": data.policy_profile_id,
                "workspace_name": workspace.name,
            },
            request=request,
        )

        return WorkspaceResponse.model_validate(workspace)
    except WorkspaceNotFoundError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.policy_profile.attach",
            status="fail",
            resource_type="workspace",
            resource_id=workspace_id,
            meta={"reason": "workspace_not_found"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PolicyProfileNotFoundError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.policy_profile.attach",
            status="fail",
            resource_type="workspace",
            resource_id=workspace_id,
            meta={
                "reason": "policy_not_found",
                "policy_profile_id": data.policy_profile_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PolicyProfileNotInTenantError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workspace.policy_profile.attach",
            status="fail",
            resource_type="workspace",
            resource_id=workspace_id,
            meta={
                "reason": "policy_wrong_tenant",
                "policy_profile_id": data.policy_profile_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# =============================================================================
# Policy Resolution (Admin only)
# =============================================================================


@policy_resolve_router.get(
    "/resolve",
    response_model=PolicyResolveResponse,
    summary="Resolve effective policy",
    description="Resolve the effective policy for the current context. Requires ADMIN role.",
)
async def resolve_policy(
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
    workflow_name: Annotated[
        str | None,
        Query(description="Optional workflow name to check against allowlist"),
    ] = None,
) -> PolicyResolveResponse:
    """Resolve the effective policy for the current context.

    Resolution order:
    1. Workspace policy profile (if set)
    2. Tenant default policy profile (if exists)
    3. Built-in restrictive default policy

    Optionally checks if a specific workflow is allowed.
    """
    service = PolicyService(db)
    resolved = await service.resolve(ctx, workflow_name)

    return PolicyResolveResponse(
        policy_profile_id=resolved.policy_profile_id,
        policy_profile_name=resolved.policy_profile_name,
        source=resolved.source,
        config=resolved.config.model_dump(),
        workflow_allowed=resolved.workflow_allowed,
        workflow_denied_reason=resolved.workflow_denied_reason,
    )
