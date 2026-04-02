"""Proactive heartbeat behaviors for Amin.

Generates contextual proactive messages based on time of day,
user activity patterns, and recent conversation history.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Conversation, Message
from src.models.twin import UserTwin
from src.services.agent.llm_router import chat_completion
from src.services.agent.twin_manager import TwinManager

logger = logging.getLogger(__name__)


class HeartbeatService:
    """Checks for and generates proactive Amin messages."""

    @staticmethod
    async def check_and_generate(
        db: AsyncSession,
        user_id: str,
        workspace_id: str,
    ) -> dict[str, Any] | None:
        """Check if a proactive message should be sent.

        Returns an event dict {"type": "heartbeat", "content": "...", "heartbeat_kind": "..."}
        or None if no proactive message is warranted.
        """
        twin = await TwinManager.get_or_create_twin(db, user_id)
        now = datetime.now(timezone.utc)
        hour = now.hour

        # Morning briefing: 5 AM - 11 AM UTC, once per day
        if 5 <= hour <= 11:
            last_briefing = (twin.work_patterns or {}).get("last_daily_briefing")
            if not _is_same_day(last_briefing, now):
                content = await HeartbeatService._morning_briefing(
                    db, user_id, workspace_id, twin
                )
                if content:
                    patterns = dict(twin.work_patterns or {})
                    patterns["last_daily_briefing"] = now.isoformat()
                    twin.work_patterns = patterns
                    await db.flush()
                    return {
                        "type": "heartbeat",
                        "content": content,
                        "heartbeat_kind": "morning_briefing",
                    }

        # Evening check-in: after 6 PM UTC, once per day
        if hour >= 18:
            last_evening = (twin.work_patterns or {}).get("last_evening_summary")
            if not _is_same_day(last_evening, now):
                content = await HeartbeatService._evening_summary(
                    db, user_id, workspace_id
                )
                if content:
                    patterns = dict(twin.work_patterns or {})
                    patterns["last_evening_summary"] = now.isoformat()
                    twin.work_patterns = patterns
                    await db.flush()
                    return {
                        "type": "heartbeat",
                        "content": content,
                        "heartbeat_kind": "evening_summary",
                    }

        return None

    @staticmethod
    async def _morning_briefing(
        db: AsyncSession,
        user_id: str,
        workspace_id: str,
        twin: UserTwin,
    ) -> str | None:
        """Generate a morning briefing based on recent activity."""
        # Gather recent conversation context
        recent_convs = await db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.workspace_id == workspace_id,
                Conversation.status == "active",
            )
            .order_by(Conversation.updated_at.desc())
            .limit(5)
        )
        convs = list(recent_convs.scalars().all())

        if not convs:
            return (
                "صباح الخير يا مستشار — Good morning, counselor. "
                "I'm ready to assist you today. What would you like to work on?"
            )

        conv_summaries: list[str] = []
        for c in convs:
            title = c.title or "Untitled"
            last_msg_q = await db.execute(
                select(Message.content)
                .where(Message.conversation_id == c.id, Message.role == "user")
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            last_msg = last_msg_q.scalar_one_or_none()
            preview = (last_msg or "")[:100]
            conv_summaries.append(f"- {title}: {preview}")

        prefs = twin.preferences or {}
        lang = prefs.get("preferred_language", "en")
        greeting = "صباح الخير يا مستشار" if lang == "ar" else "Good morning, counselor"

        try:
            response = await chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Amin, an AI legal colleague. Generate a brief morning briefing "
                            "for a GCC lawyer. Be warm, professional, and concise (under 150 words). "
                            "Mention their recent active matters and suggest priorities for the day."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Greeting: {greeting}\n\n"
                            f"Recent active conversations:\n" + "\n".join(conv_summaries) + "\n\n"
                            f"User preferences: {prefs}\n\n"
                            f"Generate a personalized morning briefing."
                        ),
                    },
                ],
                tools=None,
                model="gpt-4o-mini",
            )
            return response.choices[0].message.content or None
        except Exception as e:
            logger.warning("Morning briefing generation failed: %s", e)
            matter_list = ", ".join(c.title or "Untitled" for c in convs[:3])
            return (
                f"{greeting}. You have {len(convs)} active matter(s): {matter_list}. "
                f"How would you like to start today?"
            )

    @staticmethod
    async def _evening_summary(
        db: AsyncSession,
        user_id: str,
        workspace_id: str,
    ) -> str | None:
        """Generate an evening summary of the day's work."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        msg_count_q = await db.execute(
            select(func.count())
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.user_id == user_id,
                Conversation.workspace_id == workspace_id,
                Message.created_at >= today_start,
            )
        )
        today_messages = msg_count_q.scalar() or 0

        if today_messages < 4:
            return None

        conv_count_q = await db.execute(
            select(func.count(func.distinct(Conversation.id)))
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.user_id == user_id,
                Conversation.workspace_id == workspace_id,
                Message.created_at >= today_start,
            )
        )
        today_convs = conv_count_q.scalar() or 0

        try:
            response = await chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Amin, an AI legal colleague. Generate a brief evening wrap-up "
                            "(under 80 words). Acknowledge the day's work and offer to summarize "
                            "or pick up tomorrow."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Today's activity: {today_messages} messages across {today_convs} conversation(s). "
                            f"Generate a brief evening check-in."
                        ),
                    },
                ],
                tools=None,
                model="gpt-4o-mini",
            )
            return response.choices[0].message.content or None
        except Exception as e:
            logger.warning("Evening summary generation failed: %s", e)
            return (
                f"You've had a productive day — {today_messages} exchanges across "
                f"{today_convs} matter(s). Would you like me to summarize today's work, "
                f"or shall we pick up tomorrow?"
            )


def _is_same_day(iso_str: str | None, now: datetime) -> bool:
    """Check if an ISO timestamp string is on the same UTC day as now."""
    if not iso_str:
        return False
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.date() == now.date()
    except (ValueError, TypeError):
        return False
