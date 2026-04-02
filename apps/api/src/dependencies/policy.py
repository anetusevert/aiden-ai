"""Policy enforcement dependencies.

This module provides centralized enforcement helpers for policy checks.
Use these dependencies in workflow endpoints to ensure consistent policy enforcement.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import RequestContext, get_workspace_context
from src.schemas.policy import ResolvedPolicy
from src.services.policy_service import PolicyService


class WorkflowNotAllowedError(Exception):
    """Raised when a workflow is not allowed by policy."""

    def __init__(self, workflow_name: str, reason: str):
        self.workflow_name = workflow_name
        self.reason = reason
        super().__init__(reason)


async def require_workflow_allowed(
    ctx: RequestContext,
    workflow_name: str,
    db: AsyncSession,
) -> ResolvedPolicy:
    """Enforce that a workflow is allowed by the effective policy.

    This is the single source of truth for workflow policy enforcement.
    Call this function before executing any workflow to ensure it's permitted.

    Args:
        ctx: The request context with tenant/workspace info
        workflow_name: The workflow identifier to check (e.g., "CONTRACT_REVIEW_V1")
        db: Async database session

    Returns:
        ResolvedPolicy with the effective policy configuration

    Raises:
        HTTPException(403): If the workflow is not allowed by policy
    """
    service = PolicyService(db)
    resolved = await service.resolve(ctx, workflow_name)

    if not resolved.workflow_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=resolved.workflow_denied_reason
            or f"Workflow '{workflow_name}' is not allowed by policy",
        )

    return resolved


class WorkflowEnforcer:
    """Dependency factory for workflow enforcement.

    Use this as a FastAPI dependency to enforce workflow permissions:

    Example:
        @router.post("/contracts/review")
        async def review_contract(
            policy: Annotated[ResolvedPolicy, Depends(WorkflowEnforcer("CONTRACT_REVIEW_V1"))],
        ):
            # Workflow is allowed, proceed with execution
            ...
    """

    def __init__(self, workflow_name: str):
        """Initialize the enforcer with a workflow name.

        Args:
            workflow_name: The workflow identifier to enforce
        """
        self.workflow_name = workflow_name

    async def __call__(
        self,
        ctx: Annotated[RequestContext, Depends(get_workspace_context)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> ResolvedPolicy:
        """Enforce the workflow policy.

        Returns:
            ResolvedPolicy if workflow is allowed

        Raises:
            HTTPException(403): If workflow is not allowed
        """
        return await require_workflow_allowed(ctx, self.workflow_name, db)


def require_workflow(workflow_name: str) -> WorkflowEnforcer:
    """Create a workflow enforcement dependency.

    This is the recommended way to enforce workflow policies in endpoints.

    Usage:
        @router.post("/contracts/review")
        async def review_contract(
            policy: Annotated[ResolvedPolicy, Depends(require_workflow("CONTRACT_REVIEW_V1"))],
        ):
            # At this point, workflow is confirmed allowed
            # policy.config contains the effective policy settings
            ...

    Args:
        workflow_name: The workflow identifier to enforce

    Returns:
        A WorkflowEnforcer dependency
    """
    return WorkflowEnforcer(workflow_name)
