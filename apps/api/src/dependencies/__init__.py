"""Dependencies for Aiden.ai API."""

from src.dependencies.auth import (
    RequestContext,
    get_current_membership,
    get_current_tenant,
    get_current_user,
    get_current_workspace,
    get_tenant_context,
    get_tenant_header,
    get_workspace_context,
    get_workspace_header,
    require_admin,
    require_editor,
    require_role,
    require_viewer,
)
from src.dependencies.policy import (
    WorkflowEnforcer,
    WorkflowNotAllowedError,
    require_workflow,
    require_workflow_allowed,
)

__all__ = [
    "RequestContext",
    "get_tenant_header",
    "get_workspace_header",
    "get_current_tenant",
    "get_current_user",
    "get_current_workspace",
    "get_current_membership",
    "get_tenant_context",
    "get_workspace_context",
    "require_admin",
    "require_editor",
    "require_viewer",
    "require_role",
    # Policy enforcement
    "require_workflow",
    "require_workflow_allowed",
    "WorkflowEnforcer",
    "WorkflowNotAllowedError",
]
