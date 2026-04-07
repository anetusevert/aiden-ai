"""Admin settings routes — LLM provider configuration.

Admins can configure the LLM provider (OpenAI, etc.) and API key
from the application UI. Settings are stored in workspace.settings JSONB.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, require_admin

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


class LLMConfigResponse(BaseModel):
    provider: str
    model: str | None
    api_key_set: bool
    api_key_preview: str | None


class LLMConfigUpdate(BaseModel):
    provider: str = "openai"
    model: str | None = "gpt-4o"
    api_key: str | None = None


class LLMTestResponse(BaseModel):
    success: bool
    provider: str
    model: str
    message: str


def _get_llm_config(workspace) -> dict:
    """Extract LLM config from workspace settings."""
    ws_settings = workspace.settings or {}
    return ws_settings.get("llm_config", {})


def _mask_key(key: str | None) -> str | None:
    """Show only last 4 characters of an API key."""
    if not key or len(key) < 8:
        return None
    return f"{'•' * (len(key) - 4)}{key[-4:]}"


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    ctx: Annotated[RequestContext, Depends(require_admin())],
):
    """Get current LLM configuration (API key masked)."""
    from src.config import settings as env_settings

    config = _get_llm_config(ctx.workspace)

    provider = config.get("provider") or env_settings.llm_provider
    model = config.get("model") or env_settings.llm_model
    api_key = config.get("api_key") or env_settings.llm_api_key

    return LLMConfigResponse(
        provider=provider,
        model=model,
        api_key_set=bool(api_key),
        api_key_preview=_mask_key(api_key),
    )


@router.put("/llm", response_model=LLMConfigResponse)
async def update_llm_config(
    body: LLMConfigUpdate,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update LLM configuration for this workspace."""
    ws = ctx.workspace
    current_settings = dict(ws.settings or {})
    current_llm = current_settings.get("llm_config", {})

    new_config: dict = {
        "provider": body.provider,
        "model": body.model,
    }

    if body.api_key is not None:
        new_config["api_key"] = body.api_key
    elif "api_key" in current_llm:
        new_config["api_key"] = current_llm["api_key"]

    current_settings["llm_config"] = new_config
    ws.settings = current_settings

    from sqlalchemy import update
    from src.models.workspace import Workspace
    await db.execute(
        update(Workspace)
        .where(Workspace.id == ws.id)
        .values(settings=current_settings)
    )
    await db.commit()

    _invalidate_llm_cache()

    api_key = new_config.get("api_key")
    return LLMConfigResponse(
        provider=new_config["provider"],
        model=new_config.get("model"),
        api_key_set=bool(api_key),
        api_key_preview=_mask_key(api_key),
    )


@router.post("/llm/test", response_model=LLMTestResponse)
async def test_llm_connection(
    ctx: Annotated[RequestContext, Depends(require_admin())],
):
    """Test the LLM connection with current configuration."""
    from src.config import settings as env_settings

    config = _get_llm_config(ctx.workspace)
    api_key = config.get("api_key") or env_settings.llm_api_key
    provider = config.get("provider") or env_settings.llm_provider
    model = config.get("model") or env_settings.llm_model or "gpt-4o"

    if provider == "stub" or not api_key:
        return LLMTestResponse(
            success=False,
            provider=provider,
            model=model or "stub-v1",
            message="No API key configured. Set provider to 'openai' and provide an API key.",
        )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'connected' in one word."}],
            max_tokens=5,
        )
        reply = response.choices[0].message.content or ""
        return LLMTestResponse(
            success=True,
            provider=provider,
            model=model,
            message=f"Connection successful. Response: {reply.strip()}",
        )
    except Exception as e:
        return LLMTestResponse(
            success=False,
            provider=provider,
            model=model,
            message=f"Connection failed: {str(e)[:200]}",
        )


def _invalidate_llm_cache():
    """Clear the cached LLM client so it gets recreated with new settings."""
    try:
        from src.services.agent import llm_router
        llm_router._client_cache = None
    except Exception:
        pass
