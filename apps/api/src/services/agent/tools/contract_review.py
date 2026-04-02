"""Contract review workflow tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.dependencies.auth import RequestContext
        from src.models.tenant import Tenant
        from src.models.user import User
        from src.models.workspace import Workspace
        from src.models.workspace_membership import WorkspaceMembership
        from src.services.contract_review_service import run_contract_review
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

        result = await run_contract_review(
            db=db,
            ctx=ctx,
            document_id=params["document_id"],
            version_id=params["version_id"],
            review_mode="standard",
            focus_areas=params.get("focus_areas", ["liability", "termination", "governing_law"]),
            output_language="en",
            request_id=context.get("request_id"),
            evidence_scope="workspace",
        )

        content = f"**Contract Review Summary**\n\n{result.summary}\n\n"
        for f in result.findings:
            content += f"- **[{f.severity.upper()}]** {f.title}: {f.issue}\n"

        return ToolResult(
            content=content,
            data={"summary": result.summary, "findings_count": len(result.findings), "status": result.meta.status},
        )
    except Exception as e:
        return ToolResult(content="", error=f"Contract review failed: {e}")


contract_review_tool = Tool(
    name="contract_review",
    description=(
        "Review a contract or legal document for risks, compliance issues, and problematic clauses. "
        "Produces a structured risk assessment."
    ),
    parameters={
        "type": "object",
        "properties": {
            "document_id": {"type": "string", "description": "UUID of the document to review"},
            "version_id": {"type": "string", "description": "UUID of the version to review"},
            "focus_areas": {"type": "array", "items": {"type": "string"}, "description": "Specific areas to focus on"},
        },
        "required": ["document_id", "version_id"],
    },
    execute=_execute,
    read_only=True,
)
