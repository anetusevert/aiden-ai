"""Navigation tools — let Amin navigate the user to any page."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult

KNOWN_ROUTES = {
    # Core sections
    "home": "/home",
    "dashboard": "/home",
    "workflows": "/workflows",
    "clients": "/clients",
    "cases": "/cases",
    "documents": "/documents",
    "intelligence": "/intelligence",
    "knowledge": "/intelligence",
    "news": "/news",
    "account": "/account/amin",
    "settings": "/account/amin",
    "amin_settings": "/account/amin",
    # Workflow categories
    "research_workflows": "/workflows/research",
    "contract_workflows": "/workflows/contracts",
    "litigation_workflows": "/workflows/litigation",
    "corporate_workflows": "/workflows/corporate",
    "compliance_workflows": "/workflows/compliance",
    "advisory_workflows": "/workflows/advisory",
    "real_estate_workflows": "/workflows/real-estate",
    "employment_workflows": "/workflows/employment",
}


async def _navigate_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    """Send a navigate event to the user's browser via their WebSocket."""
    target = params.get("path", "").strip()
    message = params.get("message", "").strip()
    if not target:
        return ToolResult(content="", error="Missing path parameter.")

    if target in KNOWN_ROUTES:
        target = KNOWN_ROUTES[target]
    elif not target.startswith("/"):
        target = f"/{target}"

    from src.services.agent.realtime import send_user_event
    await send_user_event(
        context["user_id"],
        {
            "type": "navigate",
            "path": target,
            "message": message or f"Taking you to {target}.",
        },
    )

    return ToolResult(
        content=f"Navigating to {target}." + (f" {message}" if message else ""),
        data={"path": target},
    )


navigate_user_tool = Tool(
    name="navigate_user",
    description=(
        "Navigate the user's browser to a specific page in the application. "
        "Accepts route aliases like 'home', 'workflows', 'clients', 'cases', "
        "'documents', 'intelligence', 'news', or a full path like '/cases/abc-123'. "
        "Use this when the user asks to go somewhere, and include a short narration message "
        "when you want Amin to explain the move before the browser navigates."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Page name or path to navigate to (e.g. 'workflows', '/cases/abc-123')",
            },
            "message": {
                "type": "string",
                "description": "Optional short narration Amin should surface before navigating",
            },
        },
        "required": ["path"],
    },
    execute=_navigate_execute,
    read_only=True,
)
