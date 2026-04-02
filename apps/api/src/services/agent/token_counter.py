"""Accurate token counting via tiktoken.

Falls back to len(text)//4 heuristic if tiktoken is unavailable.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_encoding_cache: dict[str, Any] = {}
_tiktoken_available: bool | None = None


def _check_tiktoken() -> bool:
    global _tiktoken_available
    if _tiktoken_available is None:
        try:
            import tiktoken  # noqa: F401
            _tiktoken_available = True
        except ImportError:
            logger.warning("tiktoken not installed — using heuristic token counting")
            _tiktoken_available = False
    return _tiktoken_available


def get_encoding(model: str | None = None):
    """Return a cached tiktoken encoding for the given model."""
    if not _check_tiktoken():
        return None

    import tiktoken

    encoding_name = "cl100k_base"
    if model:
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            pass

    if encoding_name not in _encoding_cache:
        _encoding_cache[encoding_name] = tiktoken.get_encoding(encoding_name)
    return _encoding_cache[encoding_name]


def count_tokens(text: str, model: str | None = None) -> int:
    """Count tokens in a string. Uses tiktoken when available, else len//4."""
    if not text:
        return 0
    enc = get_encoding(model)
    if enc is None:
        return len(text) // 4
    return len(enc.encode(text))


def count_message_tokens(
    messages: list[dict[str, Any]],
    model: str | None = None,
) -> int:
    """Count tokens for a list of OpenAI chat messages.

    Accounts for per-message overhead tokens (role, separators).
    Based on OpenAI's token counting guide for gpt-4o / gpt-3.5-turbo.
    """
    enc = get_encoding(model)
    if enc is None:
        total = 0
        for msg in messages:
            total += 4  # per-message overhead
            total += len(msg.get("content", "") or "") // 4
            total += len(msg.get("role", "")) // 4
            if msg.get("tool_calls"):
                total += len(json.dumps(msg["tool_calls"])) // 4
        total += 2  # reply priming
        return total

    tokens_per_message = 3  # <|start|>role<|sep|>
    total = 0
    for msg in messages:
        total += tokens_per_message
        for key, value in msg.items():
            if value is None:
                continue
            if isinstance(value, str):
                total += len(enc.encode(value))
            elif isinstance(value, list):
                total += len(enc.encode(json.dumps(value)))
            elif isinstance(value, dict):
                total += len(enc.encode(json.dumps(value)))
        if msg.get("name"):
            total += 1  # role is always omitted when name is present
    total += 3  # reply priming tokens
    return total
