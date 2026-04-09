"""Seed router — admin-only endpoints to load/wipe demo data."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import RequestContext, require_admin
from src.services.organization_access_service import ensure_workspace_org_access
from src.services.demo_seed_service import (
    count_demo_dataset,
    seed_demo_dataset,
    wipe_demo_dataset,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/seed", tags=["seed"])


class SeedResponse(BaseModel):
    action: str
    cases_count: int
    clients_count: int
    documents_count: int = 0
    notes_count: int = 0
    events_count: int = 0
    warnings: list[str] = []


async def _get_org_id(ctx: RequestContext, db: AsyncSession) -> str:
    org_id = await ensure_workspace_org_access(
        db,
        tenant_id=ctx.tenant.id,
        workspace_id=ctx.workspace.id if ctx.workspace else "",
        workspace_name=ctx.workspace.name if ctx.workspace else None,
        user_id=ctx.user.id,
        workspace_role=ctx.role or "ADMIN",
    )
    if not org_id:
        raise HTTPException(status_code=400, detail="User is not a member of any organization")
    return org_id


@router.post("/mock-cases", response_model=SeedResponse)
async def seed_mock_cases(
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id(ctx, db)
    try:
        existing = await count_demo_dataset(db, org_id)
        had_existing = any(
            [
                existing.clients_count,
                existing.cases_count,
                existing.documents_count,
                existing.notes_count,
                existing.events_count,
            ]
        )

        if had_existing:
            await wipe_demo_dataset(ctx, db, org_id)

        summary = await seed_demo_dataset(ctx, db, org_id)
        action = "refreshed" if had_existing else "created"
        logger.info(
            "Loaded Riyadh demo dataset for org %s: %d clients, %d cases, %d documents",
            org_id,
            summary.clients_count,
            summary.cases_count,
            summary.documents_count,
        )
        return SeedResponse(
            action=action,
            cases_count=summary.cases_count,
            clients_count=summary.clients_count,
            documents_count=summary.documents_count,
            notes_count=summary.notes_count,
            events_count=summary.events_count,
            warnings=summary.warnings,
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("Failed to load Riyadh demo dataset for org %s", org_id)
        raise HTTPException(
            status_code=500,
            detail=f"Could not load demo data. {err}",
        ) from err


@router.delete("/mock-cases", response_model=SeedResponse)
async def wipe_mock_cases(
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id(ctx, db)
    try:
        summary = await wipe_demo_dataset(ctx, db, org_id)
        logger.info(
            "Wiped Riyadh demo dataset for org %s: %d cases, %d clients, %d documents",
            org_id,
            summary.cases_count,
            summary.clients_count,
            summary.documents_count,
        )
        return SeedResponse(
            action="wiped",
            cases_count=summary.cases_count,
            clients_count=summary.clients_count,
            documents_count=summary.documents_count,
            notes_count=summary.notes_count,
            events_count=summary.events_count,
            warnings=summary.warnings,
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("Failed to wipe Riyadh demo dataset for org %s", org_id)
        raise HTTPException(
            status_code=500,
            detail=f"Could not wipe demo data. {err}",
        ) from err
