"""Auto-generates conversation titles from the first exchange."""

import logging

from src.services.agent.llm_router import chat_completion

logger = logging.getLogger(__name__)


async def generate_title(user_message: str, assistant_message: str) -> str:
    """Generate a concise conversation title from the first user-assistant exchange.

    Returns a 3-8 word title. Falls back to a truncated user message
    if the LLM call fails.
    """
    try:
        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a concise 3-8 word title for a legal conversation. "
                        "The title should capture the core topic or intent. "
                        "Return ONLY the title text — no quotes, no punctuation, no explanation."
                    ),
                },
                {"role": "user", "content": user_message[:500]},
                {"role": "assistant", "content": assistant_message[:500]},
                {"role": "user", "content": "Generate a title for the above conversation."},
            ],
            tools=None,
            model="gpt-4o-mini",
        )

        title = (response.choices[0].message.content or "").strip()
        title = title.strip('"\'')
        if not title:
            return _fallback_title(user_message)
        return title[:100]

    except Exception as e:
        logger.warning("Title generation failed: %s", e)
        return _fallback_title(user_message)


def _fallback_title(user_message: str) -> str:
    """Create a simple title from the first words of the user message."""
    words = user_message.split()[:8]
    title = " ".join(words)
    if len(title) > 60:
        title = title[:57] + "..."
    return title or "New Conversation"
