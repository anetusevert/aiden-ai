"""Heartbeat tool — Amin checks for morning brief conditions."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select

from src.models.conversation import Message
from src.services.agent.tool_registry import Tool, ToolResult
from src.services.agent.twin_manager import TwinManager


def _is_same_day(iso_str: str | None, now: datetime) -> bool:
    if not iso_str:
        return False
    try:
        return datetime.fromisoformat(iso_str).date() == now.date()
    except (TypeError, ValueError):
        return False


async def _check_heartbeat(
    params: dict[str, Any], context: dict[str, Any]
) -> ToolResult:
    """Called at the start of each conversation to determine if a morning brief is needed."""
    del params

    db = context["db"]
    user_id = context["user_id"]

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_msg_count = await db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.user_id == user_id)
        .where(Message.created_at >= today_start)
    )

    twin = await TwinManager.get_or_create_twin(db, user_id)
    work_patterns = twin.work_patterns or {}

    is_first_session_today = (today_msg_count or 0) == 0
    hour = now.hour
    is_morning = 6 <= hour <= 11
    is_evening = hour >= 19

    return ToolResult(
        content="",
        data={
            "is_first_session_today": is_first_session_today,
            "is_morning": is_morning,
            "is_evening": is_evening,
            "hour": hour,
            "day_of_week": now.strftime("%A"),
            "is_sunday": now.weekday() == 6,
            "already_sent_morning_brief": _is_same_day(
                work_patterns.get("last_daily_briefing"), now
            ),
            "last_daily_briefing": work_patterns.get("last_daily_briefing"),
        },
    )


heartbeat_tool = Tool(
    name="check_heartbeat",
    description=(
        "Check whether the user needs a morning brief or has context that warrants "
        "a proactive message. Call this at the start of the first message in any session. "
        "Returns: is_first_session_today, is_morning, is_evening. If is_first_session_today "
        "and is_morning: run the morning briefing workflow from AGENTS.md."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
    execute=_check_heartbeat,
    read_only=True,
)
