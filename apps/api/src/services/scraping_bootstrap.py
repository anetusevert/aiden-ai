"""One-time bootstrap for default scraping sources.

Inserts the five production connectors if the scraping_sources table is empty.
Called from the application lifespan after platform admin bootstrap.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.scraping_source import ScrapingSource

logger = logging.getLogger(__name__)

DEFAULT_SOURCES: list[dict[str, Any]] = [
    {
        "connector_name": "ksa_boe",
        "display_name": "KSA Bureau of Experts",
        "jurisdiction": "KSA",
        "source_url": "https://laws.boe.gov.sa",
        "schedule_cron": "0 2 * * 0",
        "harvest_limit": 500,
    },
    {
        "connector_name": "ksa_moj",
        "display_name": "KSA Ministry of Justice",
        "jurisdiction": "KSA",
        "source_url": "https://portaleservices.moj.gov.sa",
        "schedule_cron": "0 3 * * 0",
        "harvest_limit": 300,
    },
    {
        "connector_name": "ksa_uaq",
        "display_name": "KSA Umm Al-Qura Gazette",
        "jurisdiction": "KSA",
        "source_url": "https://uqn.gov.sa",
        "schedule_cron": "0 4 * * 0",
        "harvest_limit": 200,
    },
    {
        "connector_name": "uae_moj",
        "display_name": "UAE Ministry of Justice",
        "jurisdiction": "UAE",
        "source_url": "https://elaws.moj.gov.ae",
        "schedule_cron": "0 2 * * 1",
        "harvest_limit": 500,
    },
    {
        "connector_name": "qatar_almeezan",
        "display_name": "Qatar Al Meezan",
        "jurisdiction": "QATAR",
        "source_url": "https://almeezan.qa",
        "schedule_cron": "0 2 * * 2",
        "harvest_limit": 500,
    },
]


async def bootstrap_scraping_sources(db: AsyncSession) -> dict[str, str | int]:
    """Insert default scraping sources if table is empty.

    Returns:
        Dict with 'action' key: 'seeded' or 'skipped', and count.
    """
    result = await db.execute(select(func.count()).select_from(ScrapingSource))
    count = result.scalar() or 0

    if count > 0:
        return {"action": "skipped", "existing": int(count)}

    for src in DEFAULT_SOURCES:
        db.add(ScrapingSource(**src))

    await db.commit()
    logger.info("Seeded %d default scraping sources", len(DEFAULT_SOURCES))
    return {"action": "seeded", "count": len(DEFAULT_SOURCES)}
