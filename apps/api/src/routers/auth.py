"""Authentication router for Aiden.ai API.

Provides endpoints for:
- Dev login (passwordless authentication for development)
- Token refresh (cookie-based rotation)
- Logout (single session)
- Logout all (all sessions)
- Current user info (/auth/me)

Authentication Flow (Cookie-based):
1. POST /auth/dev-login -> Sets access_token + refresh_token cookies
2. API requests use access_token cookie (httpOnly)
3. When access token expires, POST /auth/refresh to rotate
4. POST /auth/logout clears cookies and revokes session
5. POST /auth/logout-all invalidates all sessions

Note: This is development-grade authentication.
For production, integrate with enterprise SSO via the sso module.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.dependencies.auth import RequestContext, get_workspace_context
from src.models import RefreshSession, Tenant, User, Workspace, WorkspaceMembership
from src.schemas.auth import (
    CookieAuthResponse,
    CurrentUserResponse,
    DevLoginRequest,
    LoginRequest,
    RefreshResponse,
)
from src.services.audit_service import log_audit_event
from src.services.login_workspace_service import resolve_workspace_for_login
from src.utils.cookies import clear_auth_cookies, set_auth_cookies
from src.utils.passwords import normalize_email, verify_password
from src.utils.jwt import (
    InvalidTokenError,
    TokenExpiredError,
    TokenTypeMismatchError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


async def _create_refresh_session(
    db: AsyncSession,
    user_id: str,
    jti: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> RefreshSession:
    """Create a new refresh session in the database."""
    session = RefreshSession(
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    await db.flush()
    return session


async def _revoke_refresh_session(db: AsyncSession, jti: str) -> bool:
    """Revoke a refresh session by jti. Returns True if found and revoked."""
    result = await db.execute(
        select(RefreshSession).where(RefreshSession.jti == jti)
    )
    session = result.scalar_one_or_none()
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        return True
    return False


async def _revoke_all_user_sessions(db: AsyncSession, user_id: str) -> int:
    """Revoke all refresh sessions for a user. Returns count of revoked sessions."""
    now = datetime.now(UTC)
    result = await db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    return result.rowcount


async def _validate_refresh_session(
    db: AsyncSession,
    jti: str,
    user_id: str,
) -> RefreshSession | None:
    """Validate a refresh session exists and is not revoked/expired.

    Returns the session if valid, None otherwise.
    """
    result = await db.execute(
        select(RefreshSession).where(
            RefreshSession.jti == jti,
            RefreshSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    if not session.is_valid(datetime.now(UTC)):
        return None
    return session


def _get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract client info from request for session tracking."""
    user_agent = request.headers.get("user-agent")
    # Get client IP (consider X-Forwarded-For for proxies)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None
    return user_agent, ip_address


async def _issue_auth_session(
    *,
    db: AsyncSession,
    request: Request,
    response: Response,
    user: User,
    tenant: Tenant,
    workspace: Workspace,
    membership: WorkspaceMembership,
    audit_action: str,
    audit_meta: dict | None = None,
) -> CookieAuthResponse:
    """Create tokens, refresh session, set cookies, audit, commit."""
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        role=membership.role,
        email=user.email,
        token_version=user.token_version,
    )
    user_agent, ip_address = _get_client_info(request)
    refresh_token, jti, expires_at = create_refresh_token(
        user_id=user.id,
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        role=membership.role,
        token_version=user.token_version,
    )
    await _create_refresh_session(
        db=db,
        user_id=user.id,
        jti=jti,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await db.commit()
    set_auth_cookies(response, access_token, refresh_token)
    meta = {"email": user.email, "role": membership.role, "auth_mode": "cookie"}
    if audit_meta:
        meta.update(audit_meta)
    await log_audit_event(
        db=db,
        ctx=None,
        action=audit_action,
        status="success",
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        user_id=user.id,
        meta=meta,
        request=request,
    )
    return CookieAuthResponse(
        user_id=str(user.id),
        email=user.email,
        role=membership.role,
        expires_in=settings.access_token_expires_minutes * 60,
    )


@router.post(
    "/login",
    response_model=CookieAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign in with email and password",
)
async def login_with_password(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CookieAuthResponse:
    """Authenticate with globally unique email and password."""
    en = normalize_email(str(body.email))
    user_result = await db.execute(select(User).where(User.email_normalized == en))
    user = user_result.scalar_one_or_none()

    async def _fail(reason: str) -> None:
        await log_audit_event(
            db=db,
            ctx=None,
            action="auth.login",
            status="fail",
            tenant_id=user.tenant_id if user else None,
            user_id=user.id if user else None,
            meta={"reason": reason, "email": body.email},
            request=request,
        )
        await db.commit()

    if not user or not verify_password(body.password, user.password_hash):
        await _fail("invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        await _fail("user_inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        await _fail("tenant_not_found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    resolved = await resolve_workspace_for_login(db, user)
    if not resolved:
        await _fail("no_workspace")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No workspace access for this account",
        )
    workspace, membership = resolved

    if user.default_workspace_id is None:
        user.default_workspace_id = workspace.id
        await db.flush()

    return await _issue_auth_session(
        db=db,
        request=request,
        response=response,
        user=user,
        tenant=tenant,
        workspace=workspace,
        membership=membership,
        audit_action="auth.login",
    )


@router.post(
    "/dev-login",
    response_model=CookieAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Development login (passwordless)",
    responses={
        200: {"description": "Successfully authenticated, cookies set"},
        400: {"description": "Dev login is disabled"},
        401: {
            "description": "Invalid credentials (tenant/workspace/user not found or inactive)"
        },
    },
)
async def dev_login(
    login_request: DevLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CookieAuthResponse:
    """Passwordless dev login for development and testing.

    This endpoint allows authentication without passwords during development.
    It validates that:
    1. The tenant exists
    2. The workspace belongs to the tenant
    3. The user exists in the tenant (by email) and is active
    4. The user has a membership in the workspace

    Sets httpOnly cookies for access_token and refresh_token.
    Returns user info and session metadata (no raw tokens).

    **Security Note**: This endpoint should be disabled in production
    by setting AUTH_ALLOW_DEV_LOGIN=false.
    """
    # Check if dev login is enabled
    if not settings.auth_allow_dev_login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dev login is disabled. Set AUTH_ALLOW_DEV_LOGIN=true to enable.",
        )

    # Validate tenant exists
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == login_request.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        # Log failed auth attempt (no tenant context available)
        await log_audit_event(
            db=db,
            ctx=None,
            action="auth.dev_login",
            status="fail",
            tenant_id=login_request.tenant_id,
            meta={"reason": "tenant_not_found"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: tenant not found",
        )

    # Validate workspace exists and belongs to tenant
    workspace_result = await db.execute(
        select(Workspace).where(
            Workspace.id == login_request.workspace_id,
            Workspace.tenant_id == login_request.tenant_id,
        )
    )
    workspace = workspace_result.scalar_one_or_none()
    if not workspace:
        await log_audit_event(
            db=db,
            ctx=None,
            action="auth.dev_login",
            status="fail",
            tenant_id=login_request.tenant_id,
            workspace_id=login_request.workspace_id,
            meta={"reason": "workspace_not_found"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: workspace not found or does not belong to tenant",
        )

    # Validate user exists in tenant by email
    user_result = await db.execute(
        select(User).where(
            User.tenant_id == login_request.tenant_id,
            User.email_normalized == normalize_email(str(login_request.email)),
        )
    )
    user = user_result.scalar_one_or_none()
    if not user:
        await log_audit_event(
            db=db,
            ctx=None,
            action="auth.dev_login",
            status="fail",
            tenant_id=login_request.tenant_id,
            workspace_id=login_request.workspace_id,
            meta={"reason": "user_not_found", "email": login_request.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: user not found in tenant",
        )

    # Check user is active
    if not user.is_active:
        await log_audit_event(
            db=db,
            ctx=None,
            action="auth.dev_login",
            status="fail",
            tenant_id=login_request.tenant_id,
            workspace_id=login_request.workspace_id,
            user_id=user.id,
            meta={"reason": "user_inactive"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: user account is inactive",
        )

    # Validate user has membership in workspace
    membership_result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == login_request.workspace_id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        await log_audit_event(
            db=db,
            ctx=None,
            action="auth.dev_login",
            status="fail",
            tenant_id=login_request.tenant_id,
            workspace_id=login_request.workspace_id,
            user_id=user.id,
            meta={"reason": "no_membership"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: user is not a member of workspace",
        )

    return await _issue_auth_session(
        db=db,
        request=request,
        response=response,
        user=user,
        tenant=tenant,
        workspace=workspace,
        membership=membership,
        audit_action="auth.dev_login",
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    responses={
        200: {"description": "Successfully refreshed, new cookies set"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> RefreshResponse:
    """Refresh the access token using the refresh token cookie.

    This endpoint:
    1. Validates the refresh token from the cookie
    2. Verifies the session exists and is not revoked
    3. Rotates the refresh token (revokes old, issues new)
    4. Issues a new access token
    5. Sets new cookies

    If a revoked refresh token is reused (replay attack),
    all sessions for the user are revoked for security.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "missing_refresh_token",
                "message": "No refresh token cookie provided",
            },
        )

    try:
        payload = decode_refresh_token(refresh_token)
    except TokenExpiredError:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "refresh_expired",
                "message": "Refresh token has expired. Please sign in again.",
            },
        )
    except (InvalidTokenError, TokenTypeMismatchError) as e:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "invalid_refresh_token",
                "message": str(e),
            },
        )

    # Load user to validate token_version
    user_result = await db.execute(
        select(User).where(User.id == payload.sub)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "user_not_found",
                "message": "User no longer exists",
            },
        )

    # Check token_version matches (detects logout-all)
    if user.token_version != payload.token_version:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "token_revoked",
                "message": "Your session has been revoked. Please sign in again.",
            },
        )

    # Validate refresh session exists and is not revoked
    session = await _validate_refresh_session(db, payload.jti, payload.sub)
    if not session:
        # Check if this is a reuse attack (jti exists but is revoked)
        existing = await db.execute(
            select(RefreshSession).where(RefreshSession.jti == payload.jti)
        )
        existing_session = existing.scalar_one_or_none()
        if existing_session and existing_session.revoked_at is not None:
            # Refresh token reuse detected! Revoke all sessions for security
            await _revoke_all_user_sessions(db, payload.sub)
            await db.commit()
            clear_auth_cookies(response)

            await log_audit_event(
                db=db,
                ctx=None,
                action="auth.refresh_reuse_detected",
                status="fail",
                user_id=payload.sub,
                tenant_id=payload.tenant_id,
                meta={"jti": payload.jti},
                request=request,
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "refresh_reuse_detected",
                    "message": "Refresh token reuse detected. All sessions have been revoked for security.",
                },
            )

        # Session not found or expired
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "invalid_session",
                "message": "Session not found or expired. Please sign in again.",
            },
        )

    # Update last_used_at on old session before revoking
    session.last_used_at = datetime.now(UTC)

    # Revoke old session
    session.revoked_at = datetime.now(UTC)

    # Get user's current membership to ensure role is current
    membership_result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == payload.workspace_id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "no_membership",
                "message": "User is no longer a member of the workspace",
            },
        )

    # Create new tokens
    new_access_token = create_access_token(
        user_id=user.id,
        tenant_id=payload.tenant_id,
        workspace_id=payload.workspace_id,
        role=membership.role,
        email=user.email,
        token_version=user.token_version,
    )

    user_agent, ip_address = _get_client_info(request)
    new_refresh_token, new_jti, new_expires_at = create_refresh_token(
        user_id=user.id,
        tenant_id=payload.tenant_id,
        workspace_id=payload.workspace_id,
        role=membership.role,
        token_version=user.token_version,
    )

    # Store new refresh session
    await _create_refresh_session(
        db=db,
        user_id=user.id,
        jti=new_jti,
        expires_at=new_expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await db.commit()

    # Set new cookies
    set_auth_cookies(response, new_access_token, new_refresh_token)

    return RefreshResponse(
        expires_in=settings.access_token_expires_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout (current session)",
    responses={
        200: {"description": "Successfully logged out"},
    },
)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> dict[str, str]:
    """Logout from current session.

    This endpoint:
    1. Clears auth cookies
    2. Revokes the current refresh session (if valid token provided)

    Even if no valid refresh token is provided, cookies are cleared.
    """
    user_id = None
    tenant_id = None
    jti = None

    # Try to decode refresh token to revoke session
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = payload.sub
            tenant_id = payload.tenant_id
            jti = payload.jti
            # Revoke the session
            await _revoke_refresh_session(db, payload.jti)
            await db.commit()
        except (TokenExpiredError, InvalidTokenError, TokenTypeMismatchError):
            # Token invalid/expired - just clear cookies
            pass

    # Always clear cookies
    clear_auth_cookies(response)

    # Audit log
    await log_audit_event(
        db=db,
        ctx=None,
        action="auth.logout",
        status="success",
        user_id=user_id,
        tenant_id=tenant_id,
        meta={"jti": jti} if jti else None,
        request=request,
    )

    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current authenticated user",
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Not authenticated or invalid token"},
        403: {"description": "Token valid but user/membership no longer valid"},
    },
)
async def get_me(
    request: Request,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUserResponse:
    """Get information about the currently authenticated user.

    Returns the user's identity and their role in the current workspace context.
    This endpoint validates the JWT token and ensures the user is still active
    with valid workspace membership.

    Authentication can be via:
    - Cookie: access_token cookie (preferred)
    - Header: Authorization: Bearer <token> (dev fallback only)
    """
    # Determine auth mode from request
    auth_mode: str = "cookie"
    if request.cookies.get("access_token") is None:
        # Must have come from header
        auth_mode = "bearer"

    # Log auth.me access
    await log_audit_event(
        db=db,
        ctx=ctx,
        action="auth.me",
        status="success",
        meta={"auth_mode": auth_mode},
        request=request,
    )

    return CurrentUserResponse(
        user_id=str(ctx.user.id),
        tenant_id=str(ctx.tenant.id),
        workspace_id=str(ctx.workspace.id) if ctx.workspace else "",
        role=ctx.role or "",
        email=ctx.user.email,
        full_name=ctx.user.full_name,
        is_platform_admin=ctx.user.is_platform_admin,
        auth_mode=auth_mode,  # type: ignore
    )


@router.post(
    "/logout-all",
    status_code=status.HTTP_200_OK,
    summary="Invalidate all sessions (logout everywhere)",
    responses={
        200: {"description": "Successfully logged out from all devices"},
        401: {"description": "Not authenticated or invalid token"},
    },
)
async def logout_all(
    request: Request,
    response: Response,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Invalidate all sessions for the current user.

    This endpoint:
    1. Increments the user's token_version (invalidates all access tokens)
    2. Revokes all refresh sessions
    3. Clears cookies

    The user will need to re-authenticate on all devices.

    This is useful for:
    - Logging out from all devices
    - Security response after credential compromise
    - Force re-authentication after role/permission changes
    """
    try:
        # Increment token_version to invalidate all existing tokens
        ctx.user.token_version += 1
        db.add(ctx.user)

        # Revoke all refresh sessions
        revoked_count = await _revoke_all_user_sessions(db, ctx.user.id)

        await db.commit()

        # Clear cookies for current session
        clear_auth_cookies(response)

        # Audit log success
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="auth.logout_all",
            status="success",
            meta={
                "new_token_version": ctx.user.token_version,
                "revoked_sessions": revoked_count,
            },
            request=request,
        )

        return {"message": "Successfully logged out from all devices"}

    except Exception as e:
        # Audit log failure
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="auth.logout_all",
            status="fail",
            meta={"error": str(e)[:200]},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout from all devices",
        )
