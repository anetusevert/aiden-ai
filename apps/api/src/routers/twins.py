"""Twin (AI profile) routes.

Endpoints for viewing and updating the user's digital twin data.
All endpoints require JWT auth and workspace context.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.dependencies import RequestContext, get_workspace_context
from src.services.agent.context_builder import get_safe_voice, invalidate_twin_prefs_cache
from src.services.agent.twin_manager import TwinManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twin", tags=["twin"])

VALID_VOICES = {"onyx", "echo", "fable"}
VALID_LANGUAGES = {"en", "ar", "fr", "ur", "tl"}

PREVIEW_TEXT = (
    "Hello, I am Amin. Your AI legal assistant for the GCC. "
    "How can I help you today?"
)


# ---------- Schemas ----------


class TwinResponse(BaseModel):
    user_id: str
    profile: dict[str, Any]
    preferences: dict[str, Any]
    work_patterns: dict[str, Any]
    drafting_style: dict[str, Any]
    review_priorities: dict[str, Any]
    learned_corrections: Any
    personality_model: dict[str, Any]
    amin_voice: str
    app_language: str
    consolidated_at: str | None
    created_at: str
    updated_at: str


class TwinUpdate(BaseModel):
    profile: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None
    work_patterns: dict[str, Any] | None = None
    drafting_style: dict[str, Any] | None = None
    review_priorities: dict[str, Any] | None = None
    learned_corrections: list[Any] | None = None
    personality_model: dict[str, Any] | None = None
    amin_voice: str | None = None
    app_language: str | None = None

    @field_validator("amin_voice")
    @classmethod
    def validate_voice(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_VOICES:
            raise ValueError(f"amin_voice must be one of {sorted(VALID_VOICES)}")
        return v

    @field_validator("app_language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_LANGUAGES:
            raise ValueError(f"app_language must be one of {sorted(VALID_LANGUAGES)}")
        return v


# ---------- Helpers ----------


def normalize_app_language(value: str | None) -> str:
    """Return a supported app language code, defaulting to English."""
    if not value:
        return "en"
    normalized = value.strip().lower()
    return normalized if normalized in VALID_LANGUAGES else "en"


def _twin_to_response(twin) -> TwinResponse:
    """Build a TwinResponse from a UserTwin model instance."""
    prefs = twin.preferences or {}
    return TwinResponse(
        user_id=twin.user_id,
        profile=twin.profile or {},
        preferences=prefs,
        work_patterns=twin.work_patterns or {},
        drafting_style=twin.drafting_style or {},
        review_priorities=twin.review_priorities or {},
        learned_corrections=twin.learned_corrections or [],
        personality_model=twin.personality_model or {},
        amin_voice=get_safe_voice(prefs),
        app_language=normalize_app_language(prefs.get("app_language")),
        consolidated_at=twin.consolidated_at.isoformat() if twin.consolidated_at else None,
        created_at=twin.created_at.isoformat(),
        updated_at=twin.updated_at.isoformat(),
    )


# ---------- Endpoints ----------


@router.get("/me", response_model=TwinResponse)
async def get_my_twin(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the current user's digital twin data."""
    twin = await TwinManager.get_or_create_twin(db, ctx.user.id)
    await db.commit()
    return _twin_to_response(twin)


@router.patch("/me", response_model=TwinResponse)
async def update_my_twin(
    body: TwinUpdate,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update specific fields of the user's digital twin."""
    twin = await TwinManager.get_or_create_twin(db, ctx.user.id)

    if body.profile is not None:
        merged = {**(twin.profile or {}), **body.profile}
        twin.profile = merged
    if body.preferences is not None:
        merged = {**(twin.preferences or {}), **body.preferences}
        twin.preferences = merged
    if body.work_patterns is not None:
        merged = {**(twin.work_patterns or {}), **body.work_patterns}
        twin.work_patterns = merged
    if body.drafting_style is not None:
        merged = {**(twin.drafting_style or {}), **body.drafting_style}
        twin.drafting_style = merged
    if body.review_priorities is not None:
        merged = {**(twin.review_priorities or {}), **body.review_priorities}
        twin.review_priorities = merged
    if body.learned_corrections is not None:
        twin.learned_corrections = body.learned_corrections
    if body.personality_model is not None:
        merged = {**(twin.personality_model or {}), **body.personality_model}
        twin.personality_model = merged

    if body.amin_voice is not None or body.app_language is not None:
        prefs = {**(twin.preferences or {})}
        if body.amin_voice is not None:
            safe = body.amin_voice if body.amin_voice in VALID_VOICES else "onyx"
            prefs["amin_voice"] = safe
        if body.app_language is not None:
            prefs["app_language"] = normalize_app_language(body.app_language)
        twin.preferences = prefs

    await db.commit()
    await db.refresh(twin)
    # Invalidate Redis cache so next Amin message picks up new preferences immediately
    await invalidate_twin_prefs_cache(ctx.user.id)
    return _twin_to_response(twin)


# ---------- Voice Preview ----------


class VoicePreviewRequest(BaseModel):
    voice: str

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v: str) -> str:
        if v not in VALID_VOICES:
            raise ValueError(f"voice must be one of {sorted(VALID_VOICES)}")
        return v


@router.post("/voice-preview")
async def voice_preview(
    body: VoicePreviewRequest,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate a short TTS preview clip for the given voice."""
    # Try workspace DB key first, then fall back to env var
    api_key: str | None = None
    try:
        from src.models.workspace import Workspace

        ws = await db.get(Workspace, ctx.workspace.id)
        if ws and ws.settings:
            api_key = ws.settings.get("llm_config", {}).get("api_key") or None
    except Exception as exc:
        logger.warning("voice_preview: failed to load workspace API key: %s", exc)
    if not api_key:
        api_key = settings.llm_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS service not configured",
        )

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        response = await client.audio.speech.create(
            model="tts-1",
            voice=body.voice,  # type: ignore[arg-type]
            input=PREVIEW_TEXT,
        )

        async def _stream():
            async for chunk in response.response.aiter_bytes(4096):
                yield chunk

        return StreamingResponse(
            _stream(),
            media_type="audio/mpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.error("Voice preview TTS failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice preview generation failed",
        ) from e
