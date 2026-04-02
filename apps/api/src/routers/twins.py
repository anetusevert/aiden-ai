"""Twin (AI profile) routes.

Endpoints for viewing and updating the user's digital twin data.
All endpoints require JWT auth and workspace context.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, get_workspace_context
from src.services.agent.twin_manager import TwinManager

router = APIRouter(prefix="/twin", tags=["twin"])


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


# ---------- Endpoints ----------


@router.get("/me", response_model=TwinResponse)
async def get_my_twin(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the current user's digital twin data."""
    twin = await TwinManager.get_or_create_twin(db, ctx.user.id)
    await db.commit()

    return TwinResponse(
        user_id=twin.user_id,
        profile=twin.profile or {},
        preferences=twin.preferences or {},
        work_patterns=twin.work_patterns or {},
        drafting_style=twin.drafting_style or {},
        review_priorities=twin.review_priorities or {},
        learned_corrections=twin.learned_corrections or [],
        personality_model=twin.personality_model or {},
        consolidated_at=twin.consolidated_at.isoformat() if twin.consolidated_at else None,
        created_at=twin.created_at.isoformat(),
        updated_at=twin.updated_at.isoformat(),
    )


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

    await db.commit()
    await db.refresh(twin)

    return TwinResponse(
        user_id=twin.user_id,
        profile=twin.profile or {},
        preferences=twin.preferences or {},
        work_patterns=twin.work_patterns or {},
        drafting_style=twin.drafting_style or {},
        review_priorities=twin.review_priorities or {},
        learned_corrections=twin.learned_corrections or [],
        personality_model=twin.personality_model or {},
        consolidated_at=twin.consolidated_at.isoformat() if twin.consolidated_at else None,
        created_at=twin.created_at.isoformat(),
        updated_at=twin.updated_at.isoformat(),
    )
