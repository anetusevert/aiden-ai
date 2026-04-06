"""Client management tools for Amin."""

import logging
from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult

logger = logging.getLogger(__name__)


async def _search_clients_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from sqlalchemy import or_, select
        from src.models.client import Client

        db = context["db"]
        workspace_id = context["workspace_id"]
        query = params.get("query", "").strip()

        stmt = select(Client).where(Client.workspace_id == workspace_id)
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Client.display_name.ilike(pattern),
                    Client.email.ilike(pattern),
                    Client.company_name.ilike(pattern),
                )
            )
        stmt = stmt.order_by(Client.display_name).limit(20)

        result = await db.execute(stmt)
        clients = result.scalars().all()

        if not clients:
            return ToolResult(content="No clients found matching your search.")

        lines = [f"Found {len(clients)} client(s):\n"]
        for c in clients:
            lines.append(f"- **{c.display_name}** ({c.client_type}) — {c.email or 'No email'} [ID: {c.id}]")

        return ToolResult(content="\n".join(lines), data={"count": len(clients)})
    except Exception as e:
        return ToolResult(content="", error=f"Client search failed: {e}")


async def _create_client_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.models.client import Client

        db = context["db"]
        workspace_id = context["workspace_id"]

        client = Client(
            workspace_id=workspace_id,
            display_name=params["display_name"],
            client_type=params.get("client_type", "individual"),
            email=params.get("email"),
            phone=params.get("phone"),
            company_name=params.get("company_name"),
            notes=params.get("notes"),
        )
        db.add(client)
        await db.commit()
        await db.refresh(client)

        return ToolResult(
            content=f"Client '{client.display_name}' created successfully.",
            data={"client_id": client.id},
        )
    except Exception as e:
        return ToolResult(content="", error=f"Failed to create client: {e}")


async def _get_client_detail_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from sqlalchemy import func, select
        from src.models.case import Case
        from src.models.client import Client

        db = context["db"]
        client_id = params.get("client_id", "")

        client = await db.get(Client, client_id)
        if not client:
            return ToolResult(content="Client not found.", error="Invalid client_id")

        case_count = (await db.execute(
            select(func.count()).select_from(Case).where(Case.client_id == client_id)
        )).scalar() or 0

        info = (
            f"**{client.display_name}**\n"
            f"Type: {client.client_type}\n"
            f"Email: {client.email or '—'}\n"
            f"Phone: {client.phone or '—'}\n"
            f"Company: {client.company_name or '—'}\n"
            f"Active Cases: {case_count}\n"
            f"Notes: {client.notes or '—'}"
        )
        return ToolResult(content=info, data={"client_id": client_id})
    except Exception as e:
        return ToolResult(content="", error=f"Failed to get client detail: {e}")


search_clients_tool = Tool(
    name="search_clients",
    description="Search for clients by name, email, or company in the current workspace.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term for client name, email, or company",
            },
        },
        "required": ["query"],
    },
    execute=_search_clients_execute,
    read_only=True,
)

create_client_tool = Tool(
    name="create_client",
    description="Create a new client in the workspace. Requires at least a display name.",
    parameters={
        "type": "object",
        "properties": {
            "display_name": {"type": "string", "description": "Full name of the client"},
            "client_type": {
                "type": "string",
                "enum": ["individual", "company", "government"],
                "description": "Type of client",
            },
            "email": {"type": "string", "description": "Email address"},
            "phone": {"type": "string", "description": "Phone number"},
            "company_name": {"type": "string", "description": "Company/org name"},
            "notes": {"type": "string", "description": "Optional notes"},
        },
        "required": ["display_name"],
    },
    execute=_create_client_execute,
    read_only=False,
    requires_confirmation=True,
    risk_level="low",
    min_role="EDITOR",
)

get_client_detail_tool = Tool(
    name="get_client_detail",
    description="Get detailed information about a specific client by their ID.",
    parameters={
        "type": "object",
        "properties": {
            "client_id": {"type": "string", "description": "UUID of the client"},
        },
        "required": ["client_id"],
    },
    execute=_get_client_detail_execute,
    read_only=True,
)
