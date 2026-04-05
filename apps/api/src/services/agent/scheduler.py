"""Background scheduler for periodic Amin tasks.

Runs as an asyncio background task launched from FastAPI's lifespan.
Handles dream cycle consolidation and scraping schedule evaluation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select

logger = logging.getLogger(__name__)

DREAM_CYCLE_INTERVAL_SECONDS = 1800  # 30 minutes
SCRAPING_CHECK_INTERVAL_SECONDS = 300  # 5 minutes


class AminScheduler:
    """Manages periodic background tasks for the Amin agent."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._scraping_task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the background scheduler loops."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        self._scraping_task = asyncio.create_task(self._scraping_loop())
        logger.info(
            "AminScheduler started (dream=%ds, scraping=%ds)",
            DREAM_CYCLE_INTERVAL_SECONDS,
            SCRAPING_CHECK_INTERVAL_SECONDS,
        )

    async def stop(self) -> None:
        """Stop the background scheduler."""
        self._running = False
        for task in (self._task, self._scraping_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._task = None
        self._scraping_task = None
        logger.info("AminScheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop. Wakes every interval to run tasks."""
        # Wait a bit on startup to let the app fully initialize
        await asyncio.sleep(10)

        while self._running:
            try:
                await self._run_dream_cycles()
            except Exception as e:
                logger.error("Scheduler dream cycle error: %s", e, exc_info=True)

            try:
                await asyncio.sleep(DREAM_CYCLE_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break

    async def _run_dream_cycles(self) -> None:
        """Find users with unconsolidated observations and run dream cycles."""
        try:
            from src.database import async_session_maker
            from src.models.twin import TwinObservation
            from src.services.agent.twin_manager import TwinManager
        except ImportError as e:
            logger.warning("Cannot import dream cycle deps: %s", e)
            return

        async with async_session_maker() as db:
            result = await db.execute(
                select(TwinObservation.user_id)
                .where(TwinObservation.consolidated.is_(False))
                .group_by(TwinObservation.user_id)
                .having(func.count() >= 5)
            )
            user_ids = list(result.scalars().all())

            if not user_ids:
                return

            logger.info("Dream cycle: processing %d user(s)", len(user_ids))

            for user_id in user_ids:
                try:
                    await TwinManager.run_llm_dream_cycle(db, user_id)
                    await db.commit()
                except Exception as e:
                    logger.error("Dream cycle failed for user %s: %s", user_id, e)
                    await db.rollback()

    # --------------------------------------------------------------------- #
    # Scraping loop
    # --------------------------------------------------------------------- #

    async def _scraping_loop(self) -> None:
        """Periodically evaluate scraping schedules and launch due jobs."""
        await asyncio.sleep(15)  # let the app fully initialise

        while self._running:
            try:
                await self._check_scraping_schedules()
            except Exception as e:
                logger.error("Scraping schedule check error: %s", e, exc_info=True)

            try:
                await asyncio.sleep(SCRAPING_CHECK_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break

    async def _check_scraping_schedules(self) -> None:
        """Query due sources and fire pending jobs."""
        try:
            from croniter import croniter  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("croniter not installed — scraping scheduler disabled")
            return

        from src.database import async_session_maker
        from src.models.scraping_job import ScrapingJob
        from src.models.scraping_source import ScrapingSource
        from src.services.harvester_service import HarvesterService

        async with async_session_maker() as db:
            result = await db.execute(
                select(ScrapingSource).where(
                    and_(
                        ScrapingSource.enabled.is_(True),
                        ScrapingSource.schedule_cron.isnot(None),
                    )
                )
            )
            sources = list(result.scalars().all())

        now = datetime.now(timezone.utc)

        for source in sources:
            try:
                cron = croniter(source.schedule_cron, now)
                last_scheduled: datetime = cron.get_prev(datetime)

                if source.last_run_at is not None and source.last_run_at >= last_scheduled:
                    continue  # not due yet

                # Ensure no running job for this source
                async with async_session_maker() as db:
                    running = await db.execute(
                        select(ScrapingJob).where(
                            and_(
                                ScrapingJob.source_id == source.id,
                                ScrapingJob.status == "running",
                            )
                        )
                    )
                    if running.scalar_one_or_none() is not None:
                        continue

                async with async_session_maker() as db:
                    job = await HarvesterService.create_job(db, source.id, "scheduler")
                    logger.info(
                        "Scheduler triggered job %s for source %s (%s)",
                        job.id, source.connector_name, source.display_name,
                    )

                async def _run_in_fresh_session(job_id: str) -> None:
                    async with async_session_maker() as fresh_db:
                        await HarvesterService.run_job(fresh_db, job_id)

                asyncio.create_task(_run_in_fresh_session(job.id))

            except Exception as e:
                logger.error(
                    "Scraping schedule error for source %s: %s",
                    source.connector_name, e, exc_info=True,
                )
