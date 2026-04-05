"""Screen context persistence for Amin sessions."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from src.config import settings

SCREEN_CONTEXT_TTL_SECONDS = 30 * 60
_redis_client: redis.Redis | None = None
_in_memory_context: dict[str, dict[str, Any]] = {}


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _screen_context_key(user_id: str) -> str:
    return f"screen_context:{user_id}"


def set_session_screen_context(user_id: str, payload: dict[str, Any]) -> None:
    _in_memory_context[user_id] = payload


def get_session_screen_context(user_id: str) -> dict[str, Any] | None:
    return _in_memory_context.get(user_id)


async def store_screen_context(user_id: str, payload: dict[str, Any]) -> None:
    set_session_screen_context(user_id, payload)
    client = get_redis_client()
    await client.set(
        _screen_context_key(user_id),
        json.dumps(payload, ensure_ascii=True),
        ex=SCREEN_CONTEXT_TTL_SECONDS,
    )


async def get_screen_context(user_id: str) -> dict[str, Any] | None:
    if user_id in _in_memory_context:
        return _in_memory_context[user_id]

    client = get_redis_client()
    raw = await client.get(_screen_context_key(user_id))
    if not raw:
        return None
    payload = json.loads(raw)
    set_session_screen_context(user_id, payload)
    return payload


async def build_screen_context(user_id: str) -> str:
    payload = await get_screen_context(user_id)
    if not payload:
        return "USER IS CURRENTLY: on the dashboard. No document open."

    document = payload.get("document")
    if not document:
        route = payload.get("route", "/")
        page_title = payload.get("page_title") or "current page"
        return f"USER IS CURRENTLY: on {page_title} ({route}). No document open."

    title = document.get("title") or "Untitled document"
    doc_type = str(document.get("doc_type") or "document").upper()
    current_view = document.get("current_view") or "viewer"
    page = document.get("current_page")
    slide = document.get("current_slide")
    sheet = document.get("current_sheet")
    metadata = document.get("metadata") or {}
    page_count = metadata.get("page_count")
    slide_count = metadata.get("slide_count")

    if page is not None:
        suffix = f"page {page}"
        if page_count:
            suffix += f" of {page_count}"
    elif slide is not None:
        suffix = f"slide {slide}"
        if slide_count:
            suffix += f" of {slide_count}"
    elif sheet:
        suffix = f"sheet '{sheet}'"
    else:
        suffix = "with the document open"

    return (
        f"USER IS CURRENTLY: viewing document '{title}' ({doc_type}) "
        f"in {current_view} mode, {suffix}."
    )
