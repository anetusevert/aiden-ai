"""Clause redlines workflow tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.dependencies.auth import RequestContext
        from src.models.tenant import Tenant
        from src.models.user import User
        from src.models.workspace import Workspace
        from src.models.workspace_membership import WorkspaceMembership
        from src.services.clause_redlines_service import run_clause_redlines
        from sqlalchemy import select

        db = context["db"]
        tenant = (await db.execute(select(Tenant).where(Tenant.id == context["tenant_id"]))).scalar_one()
        user = (await db.execute(select(User).where(User.id == context["user_id"]))).scalar_one()
        workspace = (await db.execute(select(Workspace).where(Workspace.id == context["workspace_id"]))).scalar_one()
        membership = (await db.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == context["workspace_id"],
                WorkspaceMembership.user_id == context["user_id"],
            )
        )).scalar_one()

        ctx = RequestContext(tenant=tenant, user=user, workspace=workspace, membership=membership)

        result = await run_clause_redlines(
            db=db,
            ctx=ctx,
            document_id=params["document_id"],
            version_id=params["version_id"],
            jurisdiction=params.get("jurisdiction", "UAE"),
            clause_types=None,
            output_language="en",
            request_id=context.get("request_id"),
            evidence_scope="workspace",
        )

        content = f"**Clause Redlines Analysis**\n\n{result.summary}\n\n"
        for item in result.items:
            content += f"- **{item.clause_type}** [{item.severity}]: {item.issue or 'Not found'}\n"
            if item.suggested_redline:
                content += f"  Suggested: {item.suggested_redline}\n"

        return ToolResult(
            content=content,
            data={"summary": result.summary, "items_count": len(result.items), "status": result.meta.status},
        )
    except Exception as e:
        return ToolResult(content="", error=f"Clause redlines failed: {e}")


clause_redlines_tool = Tool(
    name="clause_redlines",
    description=(
        "Generate redline suggestions for specific clauses in a contract. "
        "Proposes alternative language with explanations."
    ),
    parameters={
        "type": "object",
        "properties": {
            "document_id": {"type": "string"},
            "version_id": {"type": "string"},
            "clause_text": {"type": "string", "description": "The clause text to redline"},
            "instruction": {"type": "string", "description": "What to change or improve"},
        },
        "required": ["document_id", "version_id", "clause_text"],
    },
    execute=_execute,
    read_only=False,
    requires_confirmation=True,
    risk_level="medium",
)
