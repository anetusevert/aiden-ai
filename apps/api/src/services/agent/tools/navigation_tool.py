"""Structured Amin navigation tool for HeyAmin routes."""

from __future__ import annotations

from typing import Any

from src.services.agent.realtime import send_user_event
from src.services.agent.tool_registry import Tool, ToolResult


def _resolve_path(destination: str, params: dict[str, str]) -> str:
    if destination in {"workflows", "workflow_hub"}:
        return "/workflows"
    if destination == "workflow_category":
        category = params.get("category", "").strip()
        return f"/workflows/{category}" if category else "/workflows"
    if destination == "workflow_execute":
        category = params.get("category", "").strip()
        workflow_id = params.get("workflowId", "").strip()
        if category and workflow_id:
            return f"/workflows/{category}/{workflow_id}/execute"
        return "/workflows"

    route_map = {
        "home": "/home",
        "clients": "/clients",
        "cases": "/cases",
        "documents": "/documents",
        # Use the existing route instead of a dead link.
        "intelligence": "/research",
        "news": "/news",
        "account": "/account/amin",
    }
    return route_map.get(destination, "/home")


async def _navigate_to_execute(
    params: dict[str, Any], context: dict[str, Any]
) -> ToolResult:
    destination = str(params.get("destination", "")).strip()
    raw_params = params.get("params") or {}
    message = str(params.get("message", "")).strip() or "Taking you there now."

    if not destination:
        return ToolResult(content="", error="Missing destination.")

    safe_params = {
        str(key): str(value)
        for key, value in raw_params.items()
        if value is not None
    }
    path = _resolve_path(destination, safe_params)

    await send_user_event(
        context["user_id"],
        {
            "type": "navigation_action",
            "path": path,
            "message": message,
        },
    )

    return ToolResult(
        content=message,
        data={"navigating_to": path, "message": message},
    )


navigate_to_tool = Tool(
    name="navigate_to",
    description="Navigate the user's browser to a specific page in the HeyAmin application",
    parameters={
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "enum": [
                    "home",
                    "workflows",
                    "clients",
                    "cases",
                    "documents",
                    "intelligence",
                    "news",
                    "account",
                    "workflow_hub",
                    "workflow_category",
                    "workflow_execute",
                ],
            },
            "params": {
                "type": "object",
                "description": "Optional params: category, workflowId, caseId, clientId",
                "additionalProperties": {"type": "string"},
            },
            "message": {
                "type": "string",
                "description": "Message to show the user explaining why we're navigating",
            },
        },
        "required": ["destination"],
    },
    execute=_navigate_to_execute,
    read_only=True,
)
