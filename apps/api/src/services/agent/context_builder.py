"""Builds the complete system prompt and message context for Amin.

Implements context compaction when approaching token limits.
Uses tiktoken for accurate counting, with len//4 heuristic fallback.
"""

import json
import logging
from typing import Any

from src.models.conversation import Message
from src.models.twin import UserTwin
from src.services.agent.screen_context import build_screen_context as load_screen_context
from src.services.agent.soul_loader import get_soul_system_prompt
from src.services.agent.token_counter import count_message_tokens, count_tokens

logger = logging.getLogger(__name__)

_TWIN_PREFS_TTL = 300  # 5 minutes


def _twin_prefs_key(user_id: str) -> str:
    return f"twin_prefs:{user_id}"


async def cache_twin_prefs(user_id: str, prefs: dict) -> None:
    """Cache twin preferences in Redis (5-minute TTL)."""
    try:
        from src.services.agent.screen_context import get_redis_client
        client = get_redis_client()
        await client.set(_twin_prefs_key(user_id), json.dumps(prefs), ex=_TWIN_PREFS_TTL)
    except Exception as e:
        logger.debug("Redis prefs cache write failed: %s", e)


async def invalidate_twin_prefs_cache(user_id: str) -> None:
    """Invalidate the Redis twin preferences cache for a user."""
    try:
        from src.services.agent.screen_context import get_redis_client
        client = get_redis_client()
        await client.delete(_twin_prefs_key(user_id))
    except Exception as e:
        logger.debug("Redis prefs cache invalidation failed: %s", e)

DEFAULT_MAX_TOKENS = 120_000

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "ar": "Arabic",
    "fr": "French",
    "ur": "Urdu",
    "tl": "Filipino (Tagalog)",
}

MALE_VOICES = {"onyx", "echo", "fable"}

SOUL_FILE_ORDER = ["SOUL.md", "IDENTITY.md", "AGENTS.md", "STYLE.md", "HEARTBEAT.md"]


def get_safe_voice(prefs: dict) -> str:
    """Return the user's saved voice, falling back to 'onyx' if invalid or female."""
    voice = prefs.get("amin_voice", "onyx")
    return voice if voice in MALE_VOICES else "onyx"


def _build_language_directive(twin: UserTwin | None) -> str:
    """Build the mandatory language directive that MUST be first in the prompt."""
    if twin is None:
        return "CRITICAL INSTRUCTION: You MUST respond exclusively in English.\n\n"

    prefs = twin.preferences or {}
    lang_code = prefs.get("app_language", "en")
    lang_name = LANGUAGE_NAMES.get(lang_code, "English")

    if lang_code == "en":
        return "CRITICAL INSTRUCTION: You MUST respond exclusively in English.\n\n"

    return (
        f"CRITICAL INSTRUCTION: You MUST respond exclusively in {lang_name}. "
        f"Every single word of your response must be in {lang_name}. "
        f"Do not use English under any circumstances. "
        f"This is a non-negotiable language setting chosen by the user.\n\n"
    )


def build_conversation_mode_context(screen_ctx: dict[str, Any] | None = None) -> str:
    """Inject conversation mode awareness into the system prompt."""
    del screen_ctx
    return """
## Current Session Context

### Deep Listening Mode
You distinguish three conversation states:
1. **Direct address** — User is talking to you. Message begins with "Amin", addresses
   you directly, or follows naturally from previous exchange. Respond fully.
2. **Thinking aloud** — User is processing their own thoughts. Short, fragmented message,
   no question mark, no direct address. Respond briefly or with a single clarifying prompt.
3. **Ambient dictation** — User appears to be speaking to someone else (references third
   party by name, topic is logistical/social, message reads as a statement not addressed
   to you). Do NOT respond unless legally significant content is mentioned.

Signals for ambient dictation (do not respond if any are present):
- Message addresses a human name that is not your name
- Content is social ("Yes, let's meet at 3"), logistical ("Please send it to him")
- Message is mid-sentence or appears to be a transcribed fragment

When in doubt: respond briefly, with a one-sentence prompt, not a full answer.

### Urgency vs. Impact
When helping prioritize tasks, always assess:
- Urgency: Is there a hard deadline? Is someone waiting?
- Impact: Does this affect a major matter, a key client, a regulatory requirement?
High urgency + high impact = address immediately in the response.
High urgency + low impact = note it, deal with it quickly.
Low urgency + high impact = explicitly schedule it, don't let it slip.
Low urgency + low impact = suggest deferring.
""".strip()


def _build_soul_prompt(soul: dict[str, str] | None) -> str:
    if soul:
        sections = [soul.get(filename, "") for filename in SOUL_FILE_ORDER if soul.get(filename, "")]
        if sections:
            return "\n\n---\n\n".join(sections)
    return get_soul_system_prompt()


async def build_case_context(user_id: str, db) -> str:
    """Build the active case context block for Amin's system prompt."""
    try:
        from src.models.case import Case, CaseEvent
        from src.models.client import Client
        from src.services.agent.screen_context import get_redis_client

        redis_client = get_redis_client()
        active_case_id = await redis_client.get(f"active_case:{user_id}")
        if not active_case_id:
            return "ACTIVE CASE: None. The lawyer has not opened a specific case yet.\n"

        case = await db.get(Case, active_case_id)
        if not case:
            return "ACTIVE CASE: None.\n"

        client = await db.get(Client, case.client_id)

        from sqlalchemy import select
        recent_events = await db.execute(
            select(CaseEvent)
            .where(CaseEvent.case_id == case.id)
            .order_by(CaseEvent.event_date.desc())
            .limit(3)
        )
        events_text = "\n".join([
            f"  - {e.title} ({e.event_date.strftime('%d %b')})"
            for e in recent_events.scalars()
        ])

        deadline_text = ""
        if case.next_deadline:
            deadline_text = f"{case.next_deadline.strftime('%d %B %Y')} — {case.next_deadline_description or ''}"
        else:
            deadline_text = "No deadline set"

        court_line = f"\nCourt: {case.court_name}" if case.court_name else ""
        opposing_line = f"\nOpposing Party: {case.opposing_party}" if case.opposing_party else ""

        return (
            f"\nACTIVE CASE CONTEXT:\n"
            f"The lawyer is currently working on the following case. Tailor ALL responses to this context.\n\n"
            f"Client: {client.display_name} ({client.client_type})\n"
            f"Case: {case.title}\n"
            f"Case Number: {case.case_number or 'Not assigned'}\n"
            f"Practice Area: {case.practice_area}\n"
            f"Jurisdiction: {case.jurisdiction}\n"
            f"Status: {case.status} | Priority: {case.priority}\n"
            f"Next Deadline: {deadline_text}"
            f"{court_line}"
            f"{opposing_line}\n\n"
            f"Case Brief: {case.amin_briefing or case.description or 'No brief available.'}\n\n"
            f"Recent Activity:\n{events_text or '  No recent activity.'}\n\n"
            f"You have full context of this case. When the lawyer asks for research, drafting, "
            f"analysis, or any legal assistance, relate it to this case and client unless they "
            f"explicitly ask about something else.\n"
        )
    except Exception as e:
        logger.debug("Failed to build case context: %s", e)
        return "ACTIVE CASE: None.\n"


def build_system_prompt(
    soul: dict[str, str],
    twin: UserTwin | None = None,
    screen_context_text: str | None = None,
    case_context_text: str | None = None,
) -> str:
    """Build the complete system prompt from Soul + Twin.

    IMPORTANT: language directive is always the absolute first content.
    Case context is injected after language directive but before soul context.
    """
    language_directive = _build_language_directive(twin)

    soul_prompt = _build_soul_prompt(soul)
    parts: list[str] = [language_directive + soul_prompt]

    conversation_mode = build_conversation_mode_context()
    if conversation_mode:
        parts.append(conversation_mode)

    if case_context_text:
        parts.append("## Active Case\n" + case_context_text)

    if twin is not None:
        twin_section = build_twin_context(twin)
        if twin_section:
            parts.append(twin_section)

    if screen_context_text:
        parts.append("## Screen Context\n" + screen_context_text)

    prompt = "\n\n---\n\n".join(parts)
    logger.debug("System prompt first 200 chars: %s", prompt[:200])
    return prompt


async def build_screen_context(user_id: str) -> str:
    """Load the latest screen context for a user."""
    return await load_screen_context(user_id)


def build_twin_context(twin: UserTwin) -> str:
    """Render twin data as natural language for inclusion in system prompt.

    Note: language directive is NOT added here — it's handled at the top of
    build_system_prompt to ensure it is always the very first content.
    """
    lines: list[str] = []

    lines.append("## Your Knowledge About This Lawyer")

    if twin.profile:
        lines.append("\n### Profile")
        for k, v in twin.profile.items():
            lines.append(f"- **{k}:** {v}")

    if twin.preferences:
        lines.append("\n### Preferences")
        for k, v in twin.preferences.items():
            lines.append(f"- **{k}:** {v}")

    if twin.work_patterns:
        lines.append("\n### Work Patterns")
        for k, v in twin.work_patterns.items():
            lines.append(f"- **{k}:** {v}")

    if twin.drafting_style:
        lines.append("\n### Drafting Style")
        for k, v in twin.drafting_style.items():
            lines.append(f"- **{k}:** {v}")

    if twin.review_priorities:
        lines.append("\n### Review Priorities")
        for k, v in twin.review_priorities.items():
            lines.append(f"- **{k}:** {v}")

    corrections = twin.learned_corrections
    if isinstance(corrections, list) and corrections:
        lines.append("\n### Learned Corrections (apply these going forward)")
        for c in corrections[-10:]:
            if isinstance(c, dict):
                lines.append(f"- {c.get('summary', str(c))}")
            else:
                lines.append(f"- {c}")

    if twin.personality_model:
        lines.append("\n### Personality & Communication Style")
        for k, v in twin.personality_model.items():
            lines.append(f"- **{k}:** {v}")

    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


def build_messages(
    conversation_messages: list[Message],
    system_prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[dict[str, Any]]:
    """Convert DB messages to OpenAI format with context compaction.

    Uses tiktoken for accurate token counting. If total tokens approach
    max_tokens, older messages are compacted.
    """
    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt}
    ]

    openai_msgs = _messages_to_openai(conversation_messages)
    candidate = llm_messages + openai_msgs

    estimated = count_message_tokens(candidate)
    if estimated > int(max_tokens * 0.85) and len(openai_msgs) > 10:
        openai_msgs = _compact(openai_msgs)

    llm_messages.extend(openai_msgs)
    return llm_messages


def _messages_to_openai(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert DB Message objects to OpenAI message dicts."""
    result: list[dict[str, Any]] = []
    for m in messages:
        msg: dict[str, Any] = {"role": m.role}
        if m.content is not None:
            msg["content"] = m.content
        if m.tool_calls is not None:
            msg["tool_calls"] = m.tool_calls
        if m.tool_call_id is not None:
            msg["tool_call_id"] = m.tool_call_id
        result.append(msg)
    return result


def _compact(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact older messages by summarizing them.

    Keeps the most recent 8 messages intact and summarizes older ones
    into a condensed conversation-history block.
    """
    preserve_count = 8
    if len(messages) <= preserve_count:
        return messages

    older = messages[:-preserve_count]
    recent = messages[-preserve_count:]

    summary_parts: list[str] = []
    for msg in older:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if content and role in ("user", "assistant"):
            truncated = content[:200] + ("..." if len(content) > 200 else "")
            summary_parts.append(f"[{role}]: {truncated}")

    if not summary_parts:
        return recent

    summary = "[Conversation history summary]\n" + "\n".join(summary_parts[-12:])
    compacted: list[dict[str, Any]] = [
        {"role": "user", "content": summary},
        {
            "role": "assistant",
            "content": "Understood. I have the context from our earlier discussion. How shall we proceed?",
        },
    ]
    return compacted + recent
