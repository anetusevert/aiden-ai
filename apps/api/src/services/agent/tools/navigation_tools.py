"""Navigation tools — let Amin navigate the user to any page."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult

KNOWN_ROUTES = {
    "dashboard": "/dashboard",
    "cases": "/cases",
    "clients": "/clients",
    "knowledge": "/knowledge",
    "documents": "/documents",
    "settings": "/settings",
    "calendar": "/calendar",
    "tasks": "/tasks",
    "billing": "/billing",
}


async def _navigate_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    """Send a navigate event to the user's browser via their WebSocket."""
    target = params.get("path", "").strip()
    if not target:
        return ToolResult(content="", error="Missing path parameter.")

    if target in KNOWN_ROUTES:
        target = KNOWN_ROUTES[target]
    elif not target.startswith("/"):
        target = f"/{target}"

    from src.services.agent.realtime import send_user_event
    await send_user_event(context["user_id"], {"type": "navigate", "path": target})

    return ToolResult(
        content=f"Navigating you to {target}.",
        data={"path": target},
    )


navigate_user_tool = Tool(
    name="navigate_user",
    description=(
        "Navigate the user's browser to a specific page in the application. "
        "Accepts page names like 'dashboard', 'cases', 'clients', 'knowledge', 'settings', "
        "or a full path like '/cases/abc-123'. Use this when the user asks to go somewhere."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Page name or path to navigate to (e.g. 'dashboard', '/cases/abc-123')",
            },
        },
        "required": ["path"],
    },
    execute=_navigate_execute,
    read_only=True,
)
