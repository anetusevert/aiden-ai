"""Builds the complete system prompt and message context for Amin.

Implements context compaction when approaching token limits.
Uses tiktoken for accurate counting, with len//4 heuristic fallback.
"""

import logging
from typing import Any

from src.models.conversation import Message
from src.models.twin import UserTwin
from src.services.agent.soul_loader import get_soul_system_prompt
from src.services.agent.token_counter import count_message_tokens, count_tokens

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOKENS = 120_000


def build_system_prompt(
    soul: dict[str, str],
    twin: UserTwin | None = None,
) -> str:
    """Build the complete system prompt from Soul + Twin."""
    parts: list[str] = [get_soul_system_prompt()]

    if twin is not None:
        twin_section = build_twin_context(twin)
        if twin_section:
            parts.append(twin_section)

    return "\n\n---\n\n".join(parts)


def build_twin_context(twin: UserTwin) -> str:
    """Render twin data as natural language for inclusion in system prompt."""
    lines: list[str] = ["## Your Knowledge About This Lawyer"]

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
