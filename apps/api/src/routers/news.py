"""Legal news router — DB-backed endpoints for KSA/GCC legal intelligence.

Serves persisted news items from the news_items table, populated by the
background news_service fetch loop. Replaces the old in-memory RSS cache.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import RequestContext, get_workspace_context
from src.models.news_item import NewsItem as NewsItemModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news"])

# ---------------------------------------------------------------------------
# Source catalog -- KSA / GCC legal feeds (used by news_service for RSS)
# ---------------------------------------------------------------------------


class CatalogSource(BaseModel):
    id: str
    name: str
    url: str
    category: str
    region: str
    description: str
    default_enabled: bool = True


SOURCE_CATALOG: list[CatalogSource] = [
    # ── Curated legal analysis (kept) ────────────────────────────────────
    CatalogSource(
        id="jdsupra-ksa",
        name="JD Supra - Saudi Arabia",
        url="https://www.jdsupra.com/resources/syndication/docsRSSfeed.aspx?ftype=AllContent&premium=1",
        category="analysis",
        region="KSA",
        description="Legal analysis and alerts on Saudi Arabian law from JD Supra contributors.",
        default_enabled=True,
    ),
    CatalogSource(
        id="jdsupra-me",
        name="JD Supra - Middle East",
        url="https://www.jdsupra.com/resources/syndication/docsRSSfeed.aspx?ftype=CommercialLaw&premium=1",
        category="analysis",
        region="GCC",
        description="Commercial and corporate law updates across the Middle East.",
        default_enabled=True,
    ),
    CatalogSource(
        id="mondaq-ksa",
        name="Mondaq - Saudi Arabia",
        url="https://www.mondaq.com/rss?type=area&content=article&geography=62",
        category="analysis",
        region="KSA",
        description="Legal and regulatory analysis specific to the Kingdom of Saudi Arabia.",
        default_enabled=True,
    ),
    CatalogSource(
        id="mondaq-uae",
        name="Mondaq - UAE",
        url="https://www.mondaq.com/rss?type=area&content=article&geography=60",
        category="analysis",
        region="GCC",
        description="Legal and regulatory analysis for the United Arab Emirates.",
        default_enabled=False,
    ),
    CatalogSource(
        id="tamimi",
        name="Al Tamimi & Company",
        url="https://www.tamimi.com/feed/",
        category="analysis",
        region="GCC",
        description="Leading GCC law firm covering Saudi, UAE, and wider Middle East legal developments.",
        default_enabled=True,
    ),
    CatalogSource(
        id="lexology-me",
        name="Lexology - Middle East",
        url="https://www.lexology.com/Hub/RSS",
        category="analysis",
        region="GCC",
        description="Global legal analysis hub with Middle East and GCC practice coverage.",
        default_enabled=True,
    ),
    # ── Primary government sources (new) ─────────────────────────────────
    CatalogSource(
        id="zatca",
        name="ZATCA (Zakat, Tax & Customs)",
        url="https://zatca.gov.sa/en/MediaCenter/News/Pages/rss.aspx",
        category="tax_law",
        region="KSA",
        description="Zakat, Tax and Customs Authority — tax rulings, circulars, and compliance updates.",
        default_enabled=True,
    ),
    CatalogSource(
        id="sama",
        name="SAMA (Saudi Central Bank)",
        url="https://www.sama.gov.sa/en-US/News/Pages/rss.aspx",
        category="financial_regulation",
        region="KSA",
        description="Saudi Central Bank circulars, regulatory updates, and banking supervision notices.",
        default_enabled=True,
    ),
    CatalogSource(
        id="zawya-law",
        name="Zawya - Law & Governance",
        url="https://www.zawya.com/en/rss/law",
        category="analysis",
        region="GCC",
        description="MENA legal and governance intelligence from Zawya.",
        default_enabled=False,
    ),
]

_CATALOG_BY_ID: dict[str, CatalogSource] = {s.id: s for s in SOURCE_CATALOG}


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class NewsItemResponse(BaseModel):
    id: str
    title: str
    title_ar: str | None = None
    summary: str | None = None
    url: str
    image_url: str | None = None
    source_name: str
    source_category: str
    jurisdiction: str
    published_at: str
    importance: str
    amin_summary: str | None = None
    wiki_filed: bool = False
    wiki_page_slug: str | None = None
    tags: list[str] | None = None


class LegalNewsResponse(BaseModel):
    items: list[NewsItemResponse]
    total: int
    limit: int
    offset: int


class BreakingNewsResponse(BaseModel):
    items: list[NewsItemResponse]


class WikiFilingResponse(BaseModel):
    wiki_page_slug: str
    wiki_url: str


class RefreshResponse(BaseModel):
    status: str


class SourceEntry(BaseModel):
    id: str
    name: str
    description: str
    category: str
    region: str
    enabled: bool


class SourcesResponse(BaseModel):
    sources: list[SourceEntry]


class UpdateSourcesRequest(BaseModel):
    enabled_source_ids: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_to_response(item: NewsItemModel) -> NewsItemResponse:
    return NewsItemResponse(
        id=str(item.id),
        title=item.title,
        title_ar=item.title_ar,
        summary=item.summary,
        url=item.url,
        image_url=item.image_url,
        source_name=item.source_name,
        source_category=item.source_category,
        jurisdiction=item.jurisdiction,
        published_at=item.published_at.isoformat() if item.published_at else "",
        importance=item.importance,
        amin_summary=item.amin_summary,
        wiki_filed=item.wiki_filed,
        wiki_page_slug=item.wiki_page_slug,
        tags=item.tags,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/legal", response_model=LegalNewsResponse)
async def get_legal_news(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Annotated[str | None, Query(description="Filter by source_category")] = None,
    jurisdiction: Annotated[str | None, Query(description="Filter by jurisdiction (KSA, UAE, Qatar, GCC)")] = None,
    importance: Annotated[str | None, Query(description="Filter by importance (breaking, high, normal)")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 40,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LegalNewsResponse:
    """Persisted legal news feed with optional filters."""
    stmt = select(NewsItemModel)

    if category:
        stmt = stmt.where(NewsItemModel.source_category == category)
    if jurisdiction:
        stmt = stmt.where(NewsItemModel.jurisdiction == jurisdiction)
    if importance:
        stmt = stmt.where(NewsItemModel.importance == importance)

    stmt = stmt.order_by(NewsItemModel.published_at.desc())

    # Total count (before pagination)
    from sqlalchemy import func as sa_func

    count_stmt = select(sa_func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return LegalNewsResponse(
        items=[_model_to_response(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/breaking", response_model=BreakingNewsResponse)
async def get_breaking_news(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BreakingNewsResponse:
    """Last 5 high-importance items published in the last 24 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    stmt = (
        select(NewsItemModel)
        .where(NewsItemModel.importance == "high")
        .where(NewsItemModel.published_at >= cutoff)
        .order_by(NewsItemModel.published_at.desc())
        .limit(5)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return BreakingNewsResponse(
        items=[_model_to_response(i) for i in items],
    )


@router.post("/{item_id}/file-to-wiki", response_model=WikiFilingResponse)
async def file_to_wiki(
    item_id: str,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WikiFilingResponse:
    """EDITOR+: manually trigger wiki filing for a news item."""
    if not ctx.has_role("EDITOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EDITOR role or higher required.",
        )

    result = await db.execute(
        select(NewsItemModel).where(NewsItemModel.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News item not found.")

    from src.services.wiki_service import WikiService

    wiki = WikiService(db=db)
    source_text = (
        f"# {item.title}\n\n"
        f"{item.summary or ''}\n\n"
        f"Source: {item.source_name}\n"
        f"URL: {item.url}"
    )
    source_type = "scraped_law" if item.source_category == "legislation" else "news_item"

    wiki_result = await wiki.ingest_source(
        source_text=source_text,
        source_title=item.title,
        source_type=source_type,
        org_id=None,
        user_id=str(ctx.user.id),
        metadata={
            "jurisdiction": item.jurisdiction,
            "url": item.url,
            "source": item.source_name,
            "published_at": item.published_at.isoformat(),
            "category": item.source_category,
        },
    )

    item.wiki_filed = True
    item.wiki_page_slug = wiki_result.primary_page.slug
    await db.commit()

    return WikiFilingResponse(
        wiki_page_slug=wiki_result.primary_page.slug,
        wiki_url=f"/wiki/{wiki_result.primary_page.slug}",
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_news(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
) -> RefreshResponse:
    """Trigger an immediate news fetch as a background task."""
    if not ctx.has_role("EDITOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EDITOR role or higher required.",
        )

    import asyncio

    from src.database import async_session_maker
    from src.services import news_service

    async def _run_refresh() -> None:
        async with async_session_maker() as fresh_db:
            try:
                new_count = await news_service.fetch_and_persist_news(fresh_db)
                if new_count > 0:
                    filed = await news_service.file_high_importance_to_wiki(fresh_db)
                    logger.info("Manual refresh: %d new items, %d filed to wiki", new_count, filed)
            except Exception as e:
                logger.error("Manual news refresh failed: %s", e, exc_info=True)

    asyncio.create_task(_run_refresh())
    return RefreshResponse(status="refresh started")


# ---------------------------------------------------------------------------
# Source catalog management (preserved from original)
# ---------------------------------------------------------------------------


@router.get("/sources", response_model=SourcesResponse)
async def get_news_sources(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
) -> SourcesResponse:
    """Return the full source catalog with enabled/disabled status for this workspace."""
    ws_settings = (ctx.workspace.settings if ctx.workspace and hasattr(ctx.workspace, "settings") else None) or {}
    enabled_ids = ws_settings.get("news_enabled_sources")
    has_explicit = isinstance(enabled_ids, list) and len(enabled_ids) > 0

    entries: list[SourceEntry] = []
    for src in SOURCE_CATALOG:
        enabled = (src.id in enabled_ids) if has_explicit else src.default_enabled
        entries.append(
            SourceEntry(
                id=src.id,
                name=src.name,
                description=src.description,
                category=src.category,
                region=src.region,
                enabled=enabled,
            )
        )
    return SourcesResponse(sources=entries)


@router.put("/sources", response_model=SourcesResponse)
async def update_news_sources(
    body: UpdateSourcesRequest,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SourcesResponse:
    """Admin-only: update which sources are enabled for this workspace."""
    if not ctx.has_role("ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")

    valid_ids = {s.id for s in SOURCE_CATALOG}
    invalid = [sid for sid in body.enabled_source_ids if sid not in valid_ids]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown source IDs: {invalid}",
        )

    workspace = ctx.workspace
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No workspace context.")

    settings: dict[str, Any] = dict(workspace.settings) if workspace.settings else {}
    settings["news_enabled_sources"] = body.enabled_source_ids
    workspace.settings = settings  # type: ignore[assignment]
    await db.commit()

    return await get_news_sources(ctx)
