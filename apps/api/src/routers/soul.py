"""Soul & Digital Twin admin API routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import get_current_user, require_role
from src.models.twin import UserTwin
from src.models.user import User
from src.services.agent.twin_manager import TwinManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/soul", tags=["soul"])

MATURITY_THRESHOLDS = [
    (200, "deep"),
    (80, "established"),
    (30, "developing"),
    (10, "forming"),
    (0, "nascent"),
]


def _calc_maturity(count: int) -> str:
    for threshold, label in MATURITY_THRESHOLDS:
        if count >= threshold:
            return label
    return "nascent"


def _twin_to_dict(twin: UserTwin) -> dict[str, Any]:
    return {
        "id": twin.id,
        "user_id": twin.user_id,
        "profile": twin.profile or {},
        "preferences": twin.preferences or {},
        "work_patterns": twin.work_patterns or {},
        "drafting_style": twin.drafting_style or {},
        "review_priorities": twin.review_priorities or {},
        "learned_corrections": twin.learned_corrections or [],
        "personality_model": twin.personality_model or {},
        "soul_dimensions": twin.soul_dimensions or [],
        "interaction_count": twin.interaction_count or 0,
        "maturity": _calc_maturity(twin.interaction_count or 0),
        "consolidated_at": twin.consolidated_at.isoformat() if twin.consolidated_at else None,
        "created_at": twin.created_at.isoformat() if twin.created_at else None,
        "updated_at": twin.updated_at.isoformat() if twin.updated_at else None,
    }


class SoulDocumentUpdate(BaseModel):
    document: dict[str, Any]


class TwinDocumentUpdate(BaseModel):
    document: dict[str, Any]


@router.get("")
async def get_my_soul(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the current user's soul/twin data."""
    user_id = current_user["user_id"]
    twin = await TwinManager.get_or_create_twin(db, user_id)
    await db.commit()
    return _twin_to_dict(twin)


@router.get("/admin/list")
async def admin_list_souls(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """List all users with soul summary (admin only)."""
    result = await db.execute(select(User).where(User.is_active.is_(True)))
    users = list(result.scalars().all())

    twin_result = await db.execute(select(UserTwin))
    twins_by_user = {t.user_id: t for t in twin_result.scalars().all()}

    items = []
    for u in users:
        twin = twins_by_user.get(u.id)
        count = twin.interaction_count if twin else 0
        items.append({
            "user_id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "has_twin": twin is not None,
            "interaction_count": count,
            "maturity": _calc_maturity(count),
            "consolidated_at": twin.consolidated_at.isoformat() if twin and twin.consolidated_at else None,
        })

    return {"users": items}


@router.get("/admin/{user_id}")
async def admin_get_soul_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Get full soul detail for a specific user (admin only)."""
    twin = await TwinManager.get_or_create_twin(db, user_id)
    await db.commit()

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    data = _twin_to_dict(twin)
    if user:
        data["user_email"] = user.email
        data["user_full_name"] = user.full_name
    return data


@router.put("/admin/{user_id}/profile")
async def admin_update_profile(
    user_id: str,
    body: SoulDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Update soul profile fields for a user (admin only)."""
    twin = await TwinManager.get_or_create_twin(db, user_id)
    twin.profile = {**(twin.profile or {}), **body.document}
    await db.commit()
    return _twin_to_dict(twin)


@router.put("/admin/{user_id}/twin")
async def admin_update_twin(
    user_id: str,
    body: TwinDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Update digital twin personality model for a user (admin only)."""
    twin = await TwinManager.get_or_create_twin(db, user_id)
    twin.personality_model = {**(twin.personality_model or {}), **body.document}
    await db.commit()
    return _twin_to_dict(twin)


@router.put("/admin/{user_id}/dimensions")
async def admin_update_dimensions(
    user_id: str,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Update soul dimensions for a user (admin only)."""
    dimensions = body.get("dimensions", [])
    twin = await TwinManager.get_or_create_twin(db, user_id)
    twin.soul_dimensions = dimensions
    await db.commit()
    return _twin_to_dict(twin)
