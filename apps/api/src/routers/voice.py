"""Voice WebSocket proxy — relays audio between browser and OpenAI Realtime API.

Route: ws://.../ws/voice/{conversation_id}

On connect the proxy authenticates the user via cookie/query-param JWT,
loads their twin preferences, and sends a server-side ``session.update``
to OpenAI so the correct voice and language are applied before the browser
sends any audio.
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

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "ar": "Arabic",
    "fr": "French",
    "ur": "Urdu",
    "tl": "Filipino (Tagalog)",
}


async def _load_voice_prefs(user_id: str) -> tuple[str, str]:
    """Return ``(voice, language_instruction)`` for *user_id*.

    Falls back to ``("onyx", <english instruction>)`` on any error.
    """
    from src.database import async_session_maker
    from src.services.agent.context_builder import get_safe_voice
    from src.services.agent.twin_manager import TwinManager

    try:
        async with async_session_maker() as db:
            twin = await TwinManager.get_or_create_twin(db, user_id)
            await db.commit()
            prefs = twin.preferences or {}
            voice = get_safe_voice(prefs)
            lang_code = prefs.get("app_language", "en")
    except Exception as exc:
        logger.warning("Failed to load twin prefs for voice WS: %s", exc)
        voice = "onyx"
        lang_code = "en"

    lang_name = LANGUAGE_NAMES.get(lang_code, "English")
    if lang_code == "en":
        instruction = "CRITICAL INSTRUCTION: You MUST respond exclusively in English."
    else:
        instruction = (
            f"CRITICAL INSTRUCTION: You MUST respond exclusively in {lang_name}. "
            f"Every single word of your response must be in {lang_name}. "
            f"Do not use English under any circumstances. "
            f"This is a non-negotiable language setting chosen by the user."
        )

    full_instructions = (
        f"{instruction}\n\n"
        "You are Amin, an AI legal assistant specialized in GCC and Saudi Arabian law. "
        "You are professional, concise, and helpful."
    )
    return voice, full_instructions


async def voice_ws(websocket: WebSocket, conversation_id: Optional[str] = None):
    """Proxy WebSocket that bridges the browser and OpenAI Realtime API."""
    await websocket.accept()

    # ── Auth ──────────────────────────────────────────────────────
    from src.utils.jwt import decode_access_token

    token: str | None = None
    cookies = websocket.cookies
    if "access_token" in cookies:
        token = cookies["access_token"]
    else:
        token = websocket.query_params.get("token")

    user_id: str | None = None
    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.sub
        except Exception:
            logger.debug("Voice WS: invalid JWT — continuing without user prefs")

    # ── API key ───────────────────────────────────────────────────
    api_key = getattr(settings, "openai_api_key", None) or getattr(settings, "llm_api_key", None)
    if not api_key:
        await websocket.send_json({"type": "error", "error": {"message": "OpenAI API key not configured"}})
        await websocket.close(1008)
        return

    upstream_headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1",
    }

    # ── Connect upstream ──────────────────────────────────────────
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

    # ── Server-side session.update with saved voice + language ────
    if user_id:
        try:
            voice, instructions = await _load_voice_prefs(user_id)
            session_update = json.dumps({
                "type": "session.update",
                "session": {
                    "voice": voice,
                    "instructions": instructions,
                },
            })
            await upstream_ws.send(session_update)
            logger.debug("Voice WS: sent server-side session.update voice=%s user=%s", voice, user_id)
        except Exception as exc:
            logger.warning("Voice WS: failed to send session.update: %s", exc)

    # ── Relay loops ───────────────────────────────────────────────

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
