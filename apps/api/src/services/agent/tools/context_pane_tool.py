"""Context pane tool — Amin pushes rich information cards to the UI."""

from time import time
from typing import Any

from src.services.agent.realtime import send_user_event
from src.services.agent.tool_registry import Tool, ToolResult

VALID_CARD_TYPES = [
    "client_card",
    "case_card",
    "research_card",
    "risk_card",
    "timeline_card",
    "comparison_card",
    "document_card",
    "regulatory_card",
    "priority_matrix",
    "text_card",
    "action_card",
]


async def _show_context_pane(
    params: dict[str, Any], context: dict[str, Any]
) -> ToolResult:
    card_type = params.get("card_type")
    title = params.get("title", "")
    data = params.get("data", {})
    pane_mode = params.get("pane_mode", "top_bar")
    subtitle = params.get("subtitle")
    actions = params.get("actions", [])

    if card_type not in VALID_CARD_TYPES:
        return ToolResult(content="", error=f"Invalid card type: {card_type}")

    if pane_mode not in {"top_bar", "left_panel"}:
        return ToolResult(content="", error=f"Invalid pane mode: {pane_mode}")

    timestamp = int(time() * 1000)
    card = {
        "id": f"card-{timestamp}",
        "type": card_type,
        "title": title,
        "subtitle": subtitle,
        "data": data,
        "actions": actions,
        "timestamp": timestamp,
    }

    await send_user_event(
        context["user_id"],
        {
            "type": "context_pane_push",
            "card": card,
            "pane_mode": pane_mode,
        },
    )

    return ToolResult(
        content=f"Displayed {card_type} in context pane ({pane_mode} mode).",
        data={"card_id": card["id"]},
    )


show_context_pane_tool = Tool(
    name="show_context_pane",
    description=(
        "Push a rich information card to the user's context pane. "
        "Use this instead of writing walls of text in chat when presenting "
        "structured data: client profiles, case summaries, research findings, "
        "risk analyses, regulatory frameworks, priority matrices, or comparisons. "
        "pane_mode: 'top_bar' for brief status cards, 'left_panel' for detailed analysis."
    ),
    parameters={
        "type": "object",
        "properties": {
            "card_type": {
                "type": "string",
                "enum": VALID_CARD_TYPES,
                "description": "Type of card to display",
            },
            "title": {"type": "string", "description": "Card title"},
            "subtitle": {"type": "string", "description": "Optional subtitle"},
            "pane_mode": {
                "type": "string",
                "enum": ["top_bar", "left_panel"],
                "default": "top_bar",
                "description": "top_bar: thin dismissible bar. left_panel: full 360px side panel",
            },
            "data": {
                "type": "object",
                "description": "Card-type-specific data payload",
            },
            "actions": {
                "type": "array",
                "description": "Optional action buttons [{label, event, params}]",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "event": {"type": "string"},
                        "params": {"type": "object"},
                    },
                    "required": ["label", "event"],
                },
            },
        },
        "required": ["card_type", "title", "data"],
    },
    execute=_show_context_pane,
    read_only=True,
)
