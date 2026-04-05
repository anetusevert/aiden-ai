"""Realtime helpers for Amin WebSocket sessions."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import WebSocket

_connections: dict[str, set[WebSocket]] = defaultdict(set)


async def register_connection(user_id: str, websocket: WebSocket) -> None:
    _connections[user_id].add(websocket)


async def unregister_connection(user_id: str, websocket: WebSocket) -> None:
    if user_id in _connections:
        _connections[user_id].discard(websocket)
        if not _connections[user_id]:
            _connections.pop(user_id, None)


async def send_user_event(user_id: str, payload: dict[str, Any]) -> None:
    stale: list[WebSocket] = []
    for websocket in list(_connections.get(user_id, set())):
        try:
            await websocket.send_json(payload)
        except Exception:
            stale.append(websocket)

    for websocket in stale:
        await unregister_connection(user_id, websocket)
