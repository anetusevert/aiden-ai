"""Platform operator routes (super-admin)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.platform_admin import (
    PlatformAdminContext,
    require_platform_admin_operator,
)
from src.models import Tenant, User
from src.schemas import (
    BootstrapResponse,
    TenantCreateWithBootstrap,
    TenantResponse,
    UserCreate,
    UserResponse,
)
from src.services import BootstrapService, UserService, log_audit_event
from src.services.bootstrap_service import TenantExistsError
from src.services.tenant_service import TenantService
from src.services.user_service import DuplicateUserError
from src.utils.passwords import hash_password

router = APIRouter(prefix="/operator", tags=["operator"])


class OperatorUserCreateBody(BaseModel):
    """Create user in a tenant (platform admin)."""

    email: EmailStr
    full_name: str | None = None
    password: str = Field(..., min_length=8)


class OperatorUserPatchBody(BaseModel):
    is_active: bool | None = None
    is_platform_admin: bool | None = None
    password: str | None = Field(None, min_length=8)


@router.get("/tenants", response_model=list[TenantResponse])
async def operator_list_tenants(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin_operator())],
) -> list[TenantResponse]:
    service = TenantService(db)
    tenants = await service.list_tenants()
    return [TenantResponse.model_validate(t) for t in tenants]


@router.get("/tenants/{tenant_id}")
async def operator_get_tenant(
    tenant_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin_operator())],
) -> TenantResponse:
    service = TenantService(db)
    tenant = await service.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)


@router.post("/tenants", response_model=BootstrapResponse, status_code=status.HTTP_201_CREATED)
async def operator_create_tenant(
    data: TenantCreateWithBootstrap,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin_operator())],
) -> BootstrapResponse:
    """Create organisation with bootstrap (same as POST /tenants, authenticated)."""
    service = BootstrapService(db)
    try:
        result = await service.create_tenant_with_bootstrap(data)
        await log_audit_event(
            db=db,
            ctx=None,
            action="operator.tenant.create",
            status="success",
            tenant_id=result.tenant_id,
            workspace_id=result.workspace_id,
            user_id=result.admin_user_id,
            resource_type="tenant",
            resource_id=result.tenant_id,
            meta={
                "tenant_name": result.tenant_name,
                "operator_user_id": ctx.user.id,
                "bootstrapped": data.bootstrap is not None,
            },
            request=request,
        )
        return result
    except TenantExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.get("/users", response_model=list[UserResponse])
async def operator_list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin_operator())],
    tenant_id: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> list[UserResponse]:
    stmt = select(User).order_by(User.created_at)
    if tenant_id:
        stmt = stmt.where(User.tenant_id == tenant_id)
    if search:
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                User.email_normalized.ilike(q),
                User.full_name.ilike(q),
            )
        )
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    return [UserResponse.model_validate(u) for u in users]


@router.post(
    "/tenants/{tenant_id}/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def operator_create_user(
    tenant_id: Annotated[str, Path()],
    body: OperatorUserCreateBody,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin_operator())],
) -> UserResponse:
    ts = TenantService(db)
    if not await ts.get_tenant_by_id(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    svc = UserService(db)
    try:
        user = await svc.create_user(
            tenant_id,
            UserCreate(
                email=body.email,
                full_name=body.full_name,
                password=body.password,
            ),
        )
        await log_audit_event(
            db=db,
            ctx=None,
            action="operator.user.create",
            status="success",
            tenant_id=tenant_id,
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            meta={"email": user.email, "operator_user_id": ctx.user.id},
            request=request,
        )
        return UserResponse.model_validate(user)
    except DuplicateUserError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.patch("/users/{user_id}", response_model=UserResponse)
async def operator_patch_user(
    user_id: Annotated[str, Path()],
    body: OperatorUserPatchBody,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin_operator())],
) -> UserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_platform_admin is not None:
        user.is_platform_admin = body.is_platform_admin
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    await db.commit()
    await db.refresh(user)

    await log_audit_event(
        db=db,
        ctx=None,
        action="operator.user.patch",
        status="success",
        tenant_id=user.tenant_id,
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        meta={"operator_user_id": ctx.user.id},
        request=request,
    )
    return UserResponse.model_validate(user)
