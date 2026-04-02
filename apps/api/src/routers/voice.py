"""Voice WebSocket proxy — relays audio between browser and OpenAI Realtime API.

Route: ws://.../ws/voice/{conversation_id}
"""

import asyncio
import json
import logging
from typing import Optional

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from src.config import settings

logger = logging.getLogger(__name__)

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"


async def voice_ws(websocket: WebSocket, conversation_id: Optional[str] = None):
    """Proxy WebSocket that bridges the browser and OpenAI Realtime API."""
    await websocket.accept()

    api_key = getattr(settings, "openai_api_key", None) or getattr(settings, "llm_api_key", None)
    if not api_key:
        await websocket.send_json({"type": "error", "error": {"message": "OpenAI API key not configured"}})
        await websocket.close(1008)
        return

    upstream_headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1",
    }

    upstream_ws = None
    try:
        upstream_ws = await websockets.connect(
            OPENAI_REALTIME_URL,
            additional_headers=upstream_headers,
            max_size=16 * 1024 * 1024,
        )
    except Exception as e:
        logger.error("Failed to connect to OpenAI Realtime: %s", e)
        await websocket.send_json({"type": "error", "error": {"message": f"Upstream connection failed: {e}"}})
        await websocket.close(1011)
        return

    async def browser_to_openai():
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "amin.ping":
                        await websocket.send_json({"type": "amin.pong"})
                        continue
                    await upstream_ws.send(data)
                except json.JSONDecodeError:
                    await upstream_ws.send(data)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug("browser_to_openai ended: %s", e)

    async def openai_to_browser():
        try:
            async for message in upstream_ws:
                if isinstance(message, str):
                    await websocket.send_text(message)
                elif isinstance(message, bytes):
                    await websocket.send_bytes(message)
        except Exception as e:
            logger.debug("openai_to_browser ended: %s", e)

    try:
        await asyncio.gather(
            browser_to_openai(),
            openai_to_browser(),
        )
    except Exception:
        pass
    finally:
        if upstream_ws:
            await upstream_ws.close()
        try:
            await websocket.close()
        except Exception:
            pass
