"""Legal research workflow tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.dependencies.auth import RequestContext
        from src.models.tenant import Tenant
        from src.models.user import User
        from src.models.workspace import Workspace
        from src.models.workspace_membership import WorkspaceMembership
        from src.services.research_service import run_legal_research
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

        result = await run_legal_research(
            db=db,
            ctx=ctx,
            question=params["question"],
            limit=10,
            filters=None,
            output_language="en",
            request_id=context.get("request_id"),
            evidence_scope="both",
        )

        content = result.answer_text
        return ToolResult(
            content=content,
            data={
                "status": result.meta.status,
                "citation_count": len(result.citations),
                "evidence_count": len(result.evidence),
            },
        )
    except Exception as e:
        return ToolResult(content="", error=f"Legal research failed: {e}")


legal_research_tool = Tool(
    name="legal_research",
    description=(
        "Conduct in-depth legal research on a topic. Analyzes relevant laws, regulations, "
        "and precedents to produce a structured research memo with citations."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The legal research question"},
            "jurisdiction": {"type": "string", "default": "KSA"},
            "context": {"type": "string", "description": "Additional context about the matter"},
        },
        "required": ["question"],
    },
    execute=_execute,
    read_only=True,
)
