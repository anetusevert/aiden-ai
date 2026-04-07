"""Extends the existing LLM provider with streaming and tool-calling support.

Includes retry with exponential backoff for transient API errors.
"""

import logging
from typing import Any, AsyncIterator

from src.config import settings

logger = logging.getLogger(__name__)

_client_cache: Any = None
_client_cache_key: str | None = None


def _get_client(api_key_override: str | None = None):
    """Get or create an AsyncOpenAI client.

    Uses api_key_override (from workspace DB settings) if provided,
    otherwise falls back to env var LLM_API_KEY.
    """
    global _client_cache, _client_cache_key
    api_key = api_key_override or settings.llm_api_key
    if not api_key:
        return None
    if _client_cache is None or _client_cache_key != api_key:
        from openai import AsyncOpenAI
        _client_cache = AsyncOpenAI(api_key=api_key)
        _client_cache_key = api_key
    return _client_cache


def _build_kwargs(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    """Build the kwargs dict for OpenAI chat.completions.create."""
    kwargs: dict[str, Any] = {"model": model, "messages": messages}

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    if stream:
        kwargs["stream"] = True

    is_new_model = model.startswith(("o1", "o3", "gpt-5", "gpt-6"))
    if is_new_model:
        kwargs["max_completion_tokens"] = 4096
    else:
        kwargs["temperature"] = 0.3
        kwargs["max_tokens"] = 4096

    return kwargs


async def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
    api_key_override: str | None = None,
) -> Any:
    """Non-streaming completion with optional tools.

    Retries on transient OpenAI errors (rate-limit, timeout, server error)
    with exponential backoff: 1s, 2s, 4s, up to 4 attempts.
    """
    use_model = model or settings.llm_model or "gpt-4o"
    client = _get_client(api_key_override)

    if client is None:
        return _stub_completion(messages)

    kwargs = _build_kwargs(use_model, messages, tools)
    return await _call_with_retry(client, kwargs)


async def _call_with_retry(client: Any, kwargs: dict[str, Any]) -> Any:
    """Execute a chat completion call with retry logic."""
    import asyncio

    max_attempts = 4
    base_delay = 1.0

    for attempt in range(max_attempts):
        try:
            return await client.chat.completions.create(**kwargs)
        except Exception as e:
            if not _is_retryable(e):
                raise
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "LLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, max_attempts, delay, e,
            )
            await asyncio.sleep(delay)

    raise RuntimeError("Unreachable")  # pragma: no cover


async def _stream_with_retry(client: Any, kwargs: dict[str, Any]) -> Any:
    """Open a streaming connection with retry on the initial request."""
    import asyncio

    max_attempts = 4
    base_delay = 1.0

    for attempt in range(max_attempts):
        try:
            return await client.chat.completions.create(**kwargs)
        except Exception as e:
            if not _is_retryable(e):
                raise
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "LLM stream connect failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, max_attempts, delay, e,
            )
            await asyncio.sleep(delay)

    raise RuntimeError("Unreachable")  # pragma: no cover


def _is_retryable(exc: Exception) -> bool:
    """Check if an exception is transient and worth retrying."""
    try:
        import openai
        return isinstance(exc, (
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.InternalServerError,
            openai.APIConnectionError,
        ))
    except ImportError:
        return False


async def stream_chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
    api_key_override: str | None = None,
) -> AsyncIterator[Any]:
    """Streaming completion that yields delta chunks.

    Retries the initial connection on transient errors.
    Once streaming begins, errors are propagated (no mid-stream retry).
    """
    use_model = model or settings.llm_model or "gpt-4o"
    client = _get_client(api_key_override)

    if client is None:
        yield _stub_delta(messages)
        return

    kwargs = _build_kwargs(use_model, messages, tools, stream=True)
    stream = await _stream_with_retry(client, kwargs)
    async for chunk in stream:
        yield chunk


# ---------------------------------------------------------------------------
# Stub fallback (no API key configured)
# ---------------------------------------------------------------------------

class _StubChoice:
    def __init__(self, content: str) -> None:
        self.message = _StubMessage(content)
        self.finish_reason = "stop"


class _StubMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.tool_calls = None


class _StubUsage:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0


class _StubCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [_StubChoice(content)]
        self.usage = _StubUsage()
        self.model = "stub-v1"


def _stub_completion(messages: list[dict[str, Any]]) -> _StubCompletion:
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            last_user = m["content"]
            break
    return _StubCompletion(
        f"I'm running in stub mode (no LLM_API_KEY configured). "
        f"Your message: {last_user[:200]}"
    )


class _StubDelta:
    def __init__(self, content: str) -> None:
        self.content = content
        self.tool_calls = None


class _StubStreamChoice:
    def __init__(self, content: str) -> None:
        self.delta = _StubDelta(content)
        self.finish_reason = "stop"


class _StubStreamChunk:
    def __init__(self, content: str) -> None:
        self.choices = [_StubStreamChoice(content)]


def _stub_delta(messages: list[dict[str, Any]]) -> _StubStreamChunk:
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            last_user = m["content"]
            break
    return _StubStreamChunk(
        f"I'm running in stub mode. Your message: {last_user[:200]}"
    )
