"""Scraping admin API — CRUD for sources and trigger/inspect jobs."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker, get_db
from src.dependencies.platform_admin import (
    ScrapingAdminContext,
    require_scraping_admin_operator,
)
from src.harvesters.connectors import list_connectors
from src.models.legal_instrument import LegalInstrument
from src.models.scraping_job import ScrapingJob
from src.models.scraping_source import ScrapingSource
from src.services.harvester_service import HarvesterService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/operator/scraping",
    tags=["scraping"],
)


# ── Pydantic schemas ────────────────────────────────────────────────────────


class ScrapingSourceCreate(BaseModel):
    """Payload for creating a new scraping source."""

    connector_name: str
    display_name: str
    jurisdiction: str
    source_url: str | None = None
    enabled: bool = True
    schedule_cron: str | None = None
    harvest_limit: int = 500


class ScrapingSourceUpdate(BaseModel):
    """Payload for partial-updating a scraping source."""

    display_name: str | None = None
    enabled: bool | None = None
    schedule_cron: str | None = None
    harvest_limit: int | None = None


class ScrapingSourceResponse(BaseModel):
    """Wire representation of a scraping source."""

    id: str
    connector_name: str
    display_name: str
    jurisdiction: str
    source_url: str | None
    enabled: bool
    schedule_cron: str | None
    harvest_limit: int
    last_run_at: str | None
    last_job_id: str | None
    created_at: str
    updated_at: str


class ScrapingJobResponse(BaseModel):
    """Wire representation of a scraping job."""

    id: str
    source_id: str
    connector_name: str
    status: str
    triggered_by: str
    started_at: str | None
    finished_at: str | None
    items_listed: int
    items_upserted: int
    items_failed: int
    error_detail: str | None
    created_at: str


class ScrapingJobRunLogEntry(BaseModel):
    """Wire representation of one job log row."""

    source_url: str | None = None
    url: str | None = None
    result: str | None = None
    status: str | None = None
    error: str | None = None


class ScrapingJobDetailResponse(ScrapingJobResponse):
    """Detailed job response used by the UI modal."""

    run_log: list[ScrapingJobRunLogEntry] | None = None


class TriggerJobResponse(BaseModel):
    """Response after manually triggering a scraping job."""

    job_id: str
    status: str
    message: str


class ScrapingStatsResponse(BaseModel):
    """Aggregated dashboard statistics for the scraping subsystem."""

    total_instruments: int
    instruments_by_jurisdiction: dict[str, int]
    active_sources: int
    total_sources: int
    running_jobs: int
    items_harvested_24h: int
    items_harvested_7d: int
    last_harvest_at: str | None


# ── helpers ─────────────────────────────────────────────────────────────────


def _dt_str(dt: object) -> str | None:
    if dt is None:
        return None
    return str(dt)


def _source_to_response(src: ScrapingSource) -> ScrapingSourceResponse:
    return ScrapingSourceResponse(
        id=str(src.id),
        connector_name=src.connector_name,
        display_name=src.display_name,
        jurisdiction=src.jurisdiction,
        source_url=src.source_url,
        enabled=src.enabled,
        schedule_cron=src.schedule_cron,
        harvest_limit=src.harvest_limit,
        last_run_at=_dt_str(src.last_run_at),
        last_job_id=str(src.last_job_id) if src.last_job_id else None,
        created_at=str(src.created_at),
        updated_at=str(src.updated_at),
    )


def _job_to_response(job: ScrapingJob) -> ScrapingJobResponse:
    return ScrapingJobResponse(
        id=str(job.id),
        source_id=str(job.source_id),
        connector_name=job.connector_name,
        status=job.status,
        triggered_by=job.triggered_by,
        started_at=_dt_str(job.started_at),
        finished_at=_dt_str(job.finished_at),
        items_listed=job.items_listed,
        items_upserted=job.items_upserted,
        items_failed=job.items_failed,
        error_detail=job.error_detail,
        created_at=str(job.created_at),
    )


def _job_log_entry(entry: dict[str, Any]) -> ScrapingJobRunLogEntry:
    source_url = entry.get("source_url")
    url = entry.get("url")
    result = entry.get("result")
    status = entry.get("status")
    return ScrapingJobRunLogEntry(
        source_url=source_url or url,
        url=url or source_url,
        result=result or status,
        status=status or result,
        error=entry.get("error"),
    )


def _job_to_detail_response(job: ScrapingJob) -> ScrapingJobDetailResponse:
    return ScrapingJobDetailResponse(
        **_job_to_response(job).model_dump(),
        run_log=[_job_log_entry(entry) for entry in (job.run_log or [])],
    )


def _validate_cron(expression: str) -> None:
    """Validate a cron expression using croniter."""
    try:
        from croniter import croniter  # type: ignore[import-untyped]

        if not croniter.is_valid(expression):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cron expression: {expression}",
            )
    except ImportError:
        logger.warning("croniter not installed — skipping cron validation")


# ── endpoints ───────────────────────────────────────────────────────────────


@router.get("/stats", response_model=ScrapingStatsResponse)
async def get_stats(
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScrapingStatsResponse:
    """Aggregated dashboard statistics for scraping and the legal corpus."""
    now = datetime.now(UTC)

    total_result = await db.execute(
        select(sa_func.count()).select_from(LegalInstrument)
    )
    total_instruments: int = total_result.scalar_one() or 0

    jurisdiction_rows = await db.execute(
        select(LegalInstrument.jurisdiction, sa_func.count())
        .group_by(LegalInstrument.jurisdiction)
    )
    instruments_by_jurisdiction: dict[str, int] = {
        str(row[0]): int(row[1]) for row in jurisdiction_rows.all()
    }

    source_counts = await db.execute(
        select(
            sa_func.count().label("total"),
            sa_func.count()
            .filter(ScrapingSource.enabled.is_(True))
            .label("active"),
        ).select_from(ScrapingSource)
    )
    src_row: Any = source_counts.one()
    total_sources: int = int(src_row.total)
    active_sources: int = int(src_row.active)

    running_result = await db.execute(
        select(sa_func.count())
        .select_from(ScrapingJob)
        .where(ScrapingJob.status.in_(["pending", "running"]))
    )
    running_jobs: int = running_result.scalar_one() or 0

    harvest_24h_result = await db.execute(
        select(sa_func.coalesce(sa_func.sum(ScrapingJob.items_upserted), 0))
        .where(
            ScrapingJob.status == "completed",
            ScrapingJob.finished_at >= now - timedelta(hours=24),
        )
    )
    items_harvested_24h: int = int(harvest_24h_result.scalar_one())

    harvest_7d_result = await db.execute(
        select(sa_func.coalesce(sa_func.sum(ScrapingJob.items_upserted), 0))
        .where(
            ScrapingJob.status == "completed",
            ScrapingJob.finished_at >= now - timedelta(days=7),
        )
    )
    items_harvested_7d: int = int(harvest_7d_result.scalar_one())

    last_run_result = await db.execute(
        select(ScrapingJob.finished_at)
        .where(ScrapingJob.status == "completed", ScrapingJob.finished_at.is_not(None))
        .order_by(ScrapingJob.finished_at.desc())
        .limit(1)
    )
    last_finished = last_run_result.scalar_one_or_none()

    return ScrapingStatsResponse(
        total_instruments=total_instruments,
        instruments_by_jurisdiction=instruments_by_jurisdiction,
        active_sources=active_sources,
        total_sources=total_sources,
        running_jobs=running_jobs,
        items_harvested_24h=items_harvested_24h,
        items_harvested_7d=items_harvested_7d,
        last_harvest_at=str(last_finished) if last_finished else None,
    )


@router.get("/sources", response_model=list[ScrapingSourceResponse])
async def list_sources(
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ScrapingSourceResponse]:
    """List all scraping sources, most recent first."""
    result = await db.execute(
        select(ScrapingSource).order_by(ScrapingSource.created_at.desc())
    )
    return [_source_to_response(s) for s in result.scalars().all()]


@router.post("/sources", response_model=ScrapingSourceResponse, status_code=201)
async def create_source(
    body: ScrapingSourceCreate,
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScrapingSourceResponse:
    """Create a new scraping source."""
    available = list_connectors()
    if body.connector_name not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown connector '{body.connector_name}'. Available: {available}",
        )

    if body.schedule_cron is not None:
        _validate_cron(body.schedule_cron)

    source = ScrapingSource(
        connector_name=body.connector_name,
        display_name=body.display_name,
        jurisdiction=body.jurisdiction,
        source_url=body.source_url,
        enabled=body.enabled,
        schedule_cron=body.schedule_cron,
        harvest_limit=body.harvest_limit,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return _source_to_response(source)


@router.patch("/sources/{source_id}", response_model=ScrapingSourceResponse)
async def update_source(
    source_id: str,
    body: ScrapingSourceUpdate,
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScrapingSourceResponse:
    """Partial-update a scraping source."""
    result = await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    if body.display_name is not None:
        source.display_name = body.display_name
    if body.enabled is not None:
        source.enabled = body.enabled
    if body.schedule_cron is not None:
        _validate_cron(body.schedule_cron)
        source.schedule_cron = body.schedule_cron
    if body.harvest_limit is not None:
        source.harvest_limit = body.harvest_limit

    await db.commit()
    await db.refresh(source)
    return _source_to_response(source)


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a scraping source (cascades to its jobs)."""
    result = await db.execute(
        select(ScrapingSource).where(ScrapingSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
    await db.commit()


@router.post(
    "/sources/{source_id}/trigger",
    response_model=TriggerJobResponse,
    status_code=202,
)
async def trigger_job(
    source_id: str,
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TriggerJobResponse:
    """Manually trigger a scraping job for a source (runs in background)."""

    # Clean up stuck jobs so they don't permanently block new triggers via
    # the 409 concurrency guard.  "pending" > 10 min and "running" > 30 min
    # are considered abandoned (e.g. the API process restarted mid-run).
    now = datetime.now(UTC)
    stale_result = await db.execute(
        select(ScrapingJob).where(
            ScrapingJob.source_id == source_id,
            ScrapingJob.status.in_(["pending", "running"]),
        )
    )
    for stale_job in stale_result.scalars().all():
        created = stale_job.created_at.replace(tzinfo=UTC) if stale_job.created_at.tzinfo is None else stale_job.created_at
        age_minutes = (now - created).total_seconds() / 60
        threshold = 10 if stale_job.status == "pending" else 30
        if age_minutes > threshold:
            stale_job.status = "failed"
            stale_job.error_detail = (
                f"Timed out: job was stuck in {stale_job.status} for over "
                f"{threshold} minutes (likely lost during API restart)"
            )
            stale_job.finished_at = now
    await db.commit()

    job = await HarvesterService.create_job(db, source_id, "manual")

    async def _run_in_background(job_id: str) -> None:
        async with async_session_maker() as fresh_db:
            await HarvesterService.run_job(fresh_db, job_id)

    asyncio.create_task(_run_in_background(str(job.id)))

    return TriggerJobResponse(
        job_id=str(job.id),
        status=job.status,
        message="Job created and queued for execution",
    )


@router.post("/jobs/reset-stuck")
async def reset_stuck_jobs(
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Force-fail all pending/running jobs so sources can be re-triggered."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(ScrapingJob).where(
            ScrapingJob.status.in_(["pending", "running"]),
        )
    )
    orphans = result.scalars().all()
    count = 0
    for job in orphans:
        job.status = "failed"
        job.error_detail = "Manually reset by administrator"
        job.finished_at = now
        count += 1
    await db.commit()
    return {"reset_count": count, "message": f"Marked {count} stuck job(s) as failed"}


@router.get("/jobs", response_model=list[ScrapingJobResponse])
async def list_jobs(
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
    source_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ScrapingJobResponse]:
    """List scraping jobs, most recent first."""
    stmt = select(ScrapingJob).order_by(ScrapingJob.created_at.desc()).limit(limit)
    if source_id:
        stmt = stmt.where(ScrapingJob.source_id == source_id)
    result = await db.execute(stmt)
    return [_job_to_response(j) for j in result.scalars().all()]


@router.get("/jobs/{job_id}", response_model=ScrapingJobDetailResponse)
async def get_job(
    job_id: str,
    _ctx: Annotated[ScrapingAdminContext, Depends(require_scraping_admin_operator())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScrapingJobDetailResponse:
    """Get a single job detail (includes run_log via the model)."""
    result = await db.execute(
        select(ScrapingJob).where(ScrapingJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_detail_response(job)
