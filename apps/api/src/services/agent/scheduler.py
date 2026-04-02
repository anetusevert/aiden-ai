"""Background scheduler for periodic Amin tasks.

Runs as an asyncio background task launched from FastAPI's lifespan.
Currently handles dream cycle consolidation on a fixed interval.
"""

import asyncio
import logging
from typing import Any

from sqlalchemy import func, select

logger = logging.getLogger(__name__)

DREAM_CYCLE_INTERVAL_SECONDS = 1800  # 30 minutes


class AminScheduler:
    """Manages periodic background tasks for the Amin agent."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the background scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AminScheduler started (interval=%ds)", DREAM_CYCLE_INTERVAL_SECONDS)

    async def stop(self) -> None:
        """Stop the background scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
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
