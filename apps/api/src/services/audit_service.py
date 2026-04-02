"""Audit logging service for tracking user actions.

This service provides a safe, fail-closed interface for logging audit events.
It never throws exceptions that would break the main request flow.
"""

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.dependencies.auth import RequestContext
from src.middleware.request_id import get_request_id
from src.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for writing audit log entries.

    This service is designed to be fail-safe:
    - It never raises exceptions that would break the main request
    - Errors are logged but silently swallowed
    - Best-effort logging with graceful degradation

    Usage:
        audit = AuditService(db)
        await audit.log(
            ctx=request_context,
            action="tenant.create",
            status="success",
            resource_type="tenant",
            resource_id=tenant.id,
            request=request,
        )
    """

    def __init__(self, db: AsyncSession):
        """Initialize the audit service.

        Args:
            db: Async database session for writing logs
        """
        self.db = db

    async def log(
        self,
        ctx: RequestContext | None,
        action: str,
        status: str,
        *,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        meta: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> None:
        """Log an audit event.

        This method is designed to be fail-safe and will never raise exceptions
        that could break the main request flow. Errors are logged internally.

        Args:
            ctx: RequestContext with tenant/workspace/user info (can be None for pre-auth events)
            action: Action identifier (e.g., "tenant.create", "auth.dev_login")
            status: Outcome status ("success" or "fail")
            tenant_id: Override tenant_id (use if ctx is None)
            workspace_id: Override workspace_id
            user_id: Override user_id
            resource_type: Type of resource affected (e.g., "tenant", "workspace")
            resource_id: ID of the affected resource
            meta: Additional structured context (avoid storing secrets)
            request: FastAPI Request object (for IP/User-Agent extraction)
        """
        try:
            # Extract context values with fallbacks
            final_tenant_id = tenant_id
            final_workspace_id = workspace_id
            final_user_id = user_id

            if ctx is not None:
                if final_tenant_id is None:
                    final_tenant_id = ctx.tenant.id
                if final_workspace_id is None and ctx.workspace is not None:
                    final_workspace_id = ctx.workspace.id
                if final_user_id is None:
                    final_user_id = ctx.user.id

            # Tenant ID is required
            if final_tenant_id is None:
                logger.warning(
                    f"Audit log skipped: no tenant_id for action={action}"
                )
                return

            # Extract request metadata
            request_id = "unknown"
            ip = None
            user_agent = None

            if request is not None:
                request_id = get_request_id(request)
                # Get client IP (handle proxies)
                ip = self._extract_client_ip(request)
                user_agent = request.headers.get("User-Agent")
                # Truncate user agent if too long
                if user_agent and len(user_agent) > 512:
                    user_agent = user_agent[:512]

            # Add environment to meta for traceability
            final_meta = dict(meta) if meta else {}
            final_meta["environment"] = settings.environment

            # Create audit log entry
            audit_entry = AuditLog(
                tenant_id=final_tenant_id,
                workspace_id=final_workspace_id,
                user_id=final_user_id,
                request_id=request_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                meta=final_meta,
                ip=ip,
                user_agent=user_agent,
            )

            self.db.add(audit_entry)
            await self.db.commit()

        except Exception as e:
            # Never let audit logging break the main request
            logger.error(
                f"Failed to write audit log: action={action}, status={status}, error={e}"
            )
            # Attempt to rollback to avoid transaction issues
            try:
                await self.db.rollback()
            except Exception:
                pass

    def _extract_client_ip(self, request: Request) -> str | None:
        """Extract the client IP address from the request.

        Handles common proxy headers (X-Forwarded-For, X-Real-IP).

        Args:
            request: The FastAPI Request object

        Returns:
            Client IP address or None if not determinable
        """
        # Check X-Forwarded-For header (common for proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can be a comma-separated list
            # The first IP is typically the original client
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (used by some proxies)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client connection
        if request.client:
            return request.client.host

        return None


async def log_audit_event(
    db: AsyncSession,
    ctx: RequestContext | None,
    action: str,
    status: str,
    *,
    tenant_id: str | None = None,
    workspace_id: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    meta: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """Convenience function for logging audit events.

    This is a shorthand for creating an AuditService and calling log().
    Useful when you don't need to maintain a service instance.

    Args:
        db: Async database session
        ctx: RequestContext with tenant/workspace/user info
        action: Action identifier
        status: Outcome status ("success" or "fail")
        tenant_id: Override tenant_id (use if ctx is None)
        workspace_id: Override workspace_id
        user_id: Override user_id
        resource_type: Type of resource affected
        resource_id: ID of the affected resource
        meta: Additional structured context
        request: FastAPI Request object
    """
    service = AuditService(db)
    await service.log(
        ctx=ctx,
        action=action,
        status=status,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=meta,
        request=request,
    )
