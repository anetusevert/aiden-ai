"""Harvester service — bridge between connectors and the legal corpus pipeline.

Runs a scraping connector and ingests results directly into the database,
bypassing the ZIP snapshot format entirely.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.harvesters.connectors import get_connector
from src.harvesters.http import HttpClient
from src.harvesters.models import ParsedRecord
from src.models.legal_instrument import LegalInstrument
from src.models.legal_instrument_version import LegalInstrumentVersion
from src.models.scraping_job import ScrapingJob
from src.models.scraping_source import ScrapingSource

logger = logging.getLogger(__name__)

_RUN_LOG_CAP = 100


def _compute_instrument_key(jurisdiction: str, source_name: str, source_url: str) -> str:
    """Compute the instrument dedupe key (same logic as global_legal_import_service)."""
    url_hash = hashlib.sha256(source_url.encode()).hexdigest()
    return f"{jurisdiction}:{source_name}:{url_hash}"


def _normalize_instrument_type(type_guess: str | None) -> str:
    from src.models.legal_instrument import LEGAL_INSTRUMENT_TYPES

    if not type_guess:
        return "other"
    normalized = type_guess.lower().strip().replace(" ", "_").replace("-", "_")
    if normalized in LEGAL_INSTRUMENT_TYPES:
        return normalized
    return "other"


def _parse_date_guess(date_str: str | None) -> Any:
    """Parse a YYYY-MM-DD string into a date or None."""
    from datetime import date as _date

    if not date_str:
        return None
    try:
        return _date.fromisoformat(date_str[:10])
    except ValueError:
        return None


class HarvesterService:
    """Runs a scraping connector and ingests results directly into the legal corpus."""

    @staticmethod
    async def create_job(
        db: AsyncSession,
        source_id: str,
        triggered_by: str,
    ) -> ScrapingJob:
        """Create a ScrapingJob in *pending* status for the given source.

        Raises:
            HTTPException 404: source not found or disabled.
            HTTPException 409: a job is already queued or running for this source.
        """
        result = await db.execute(
            select(ScrapingSource).where(ScrapingSource.id == source_id)
        )
        source = result.scalar_one_or_none()
        if source is None:
            raise HTTPException(status_code=404, detail="Scraping source not found")
        if not source.enabled:
            raise HTTPException(status_code=400, detail="Scraping source is disabled")

        active_job = await db.execute(
            select(ScrapingJob).where(
                and_(
                    ScrapingJob.source_id == source_id,
                    ScrapingJob.status.in_(["pending", "running"]),
                )
            )
        )
        existing_job = active_job.scalar_one_or_none()
        if existing_job is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A scraping job is already queued or running for this source. "
                    "Wait for it to finish before triggering another run."
                ),
            )

        job = ScrapingJob(
            source_id=source_id,
            connector_name=source.connector_name,
            status="pending",
            triggered_by=triggered_by,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def run_job(db: AsyncSession, job_id: str) -> ScrapingJob:
        """Execute the scraping job end-to-end.

        Always leaves the job in *completed* or *failed* — never *running*.
        """
        job_result = await db.execute(
            select(ScrapingJob).where(ScrapingJob.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        if job is None:
            raise ValueError(f"ScrapingJob {job_id} not found")
        if job.status != "pending":
            raise ValueError(f"ScrapingJob {job_id} is not in pending status (is {job.status})")

        source_result = await db.execute(
            select(ScrapingSource).where(ScrapingSource.id == job.source_id)
        )
        source = source_result.scalar_one_or_none()
        if source is None:
            raise ValueError(f"ScrapingSource {job.source_id} not found")

        job.status = "running"
        job.started_at = datetime.now(UTC)
        await db.commit()

        tmp_dir = Path(tempfile.mkdtemp(prefix=f"harvester_{job_id}_"))

        try:
            connector_cls = get_connector(source.connector_name)

            http_client = HttpClient(rate=0.5, retries=3, cache_dir=None)
            connector = connector_cls(http=http_client, out_dir=tmp_dir)

            items = await asyncio.to_thread(connector.list_items, source.harvest_limit)
            job.items_listed = len(items)
            await db.commit()

            run_log: list[dict[str, Any]] = []

            for item in items:
                try:
                    record = await asyncio.to_thread(connector.fetch_and_parse, item)
                    await HarvesterService._ingest_record(db, record, job)
                    if len(run_log) < _RUN_LOG_CAP:
                        run_log.append(
                            {
                                "source_url": item.source_url,
                                "result": "ok",
                            }
                        )
                except Exception as item_err:
                    job.items_failed += 1
                    logger.warning(
                        "Item failed for job %s: %s — %s",
                        job_id, item.source_url, item_err,
                    )
                    if len(run_log) < _RUN_LOG_CAP:
                        run_log.append(
                            {
                                "source_url": item.source_url,
                                "result": "error",
                                "error": str(item_err)[:200],
                            }
                        )

            job.run_log = run_log
            job.status = "completed"
            job.finished_at = datetime.now(UTC)
            source.last_run_at = datetime.now(UTC)
            source.last_job_id = job.id
            await db.commit()

        except Exception as e:
            logger.error("Job %s failed: %s", job_id, e, exc_info=True)
            job.status = "failed"
            job.error_detail = str(e)[:2000]
            job.finished_at = datetime.now(UTC)
            await db.commit()

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        return job

    @staticmethod
    async def _ingest_record(
        db: AsyncSession,
        record: ParsedRecord,
        job: ScrapingJob,
    ) -> None:
        """Convert a ParsedRecord into the legal corpus format and upsert."""
        instrument_key = _compute_instrument_key(
            record.jurisdiction, record.source_name, record.source_url,
        )
        import_batch_id = job.id

        stmt = select(LegalInstrument).where(
            and_(
                LegalInstrument.jurisdiction == record.jurisdiction,
                LegalInstrument.instrument_key == instrument_key,
            )
        )
        existing = await db.execute(stmt)
        instrument = existing.scalar_one_or_none()

        if instrument:
            instrument.updated_at = datetime.now(UTC)
            instrument.import_batch_id = import_batch_id
        else:
            title = record.title_ar or record.title_en or record.source_url
            published_at = _parse_date_guess(record.published_at_guess)
            instrument_type = _normalize_instrument_type(record.instrument_type_guess)

            instrument = LegalInstrument(
                jurisdiction=record.jurisdiction,
                instrument_type=instrument_type,
                title=title,
                title_ar=record.title_ar,
                official_source_url=record.source_url,
                published_at=published_at,
                status="active",
                instrument_key=instrument_key,
                import_batch_id=import_batch_id,
            )
            db.add(instrument)
            await db.flush()

        version_key = record.raw_sha256
        existing_ver = await db.execute(
            select(LegalInstrumentVersion).where(
                and_(
                    LegalInstrumentVersion.legal_instrument_id == instrument.id,
                    LegalInstrumentVersion.version_key == version_key,
                )
            )
        )
        if existing_ver.scalar_one_or_none() is not None:
            job.items_upserted += 1
            return

        file_name = f"{record.raw_sha256}.html"
        version = LegalInstrumentVersion(
            legal_instrument_id=instrument.id,
            version_label="imported",
            file_name=file_name,
            content_type="text/html",
            size_bytes=0,
            storage_provider="harvester",
            storage_bucket="n/a",
            storage_key=f"harvester/{instrument.id}/{file_name}",
            sha256=record.raw_sha256,
            language="ar" if record.title_ar else "mixed",
            is_indexed=False,
            version_key=version_key,
            import_batch_id=import_batch_id,
            imported_at=datetime.now(UTC),
        )
        db.add(version)
        await db.flush()

        job.items_upserted += 1
