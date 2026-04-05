"""Legal news aggregation router.

Fetches and caches legal news from multiple RSS/Atom feeds.
Returns a unified list sorted by recency with images and source metadata.
Workspace admins can choose which catalog sources are enabled.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import RequestContext, get_workspace_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news"])

# ---------------------------------------------------------------------------
# Source catalog -- KSA / GCC legal feeds
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
    CatalogSource(
        id="jdsupra-ksa",
        name="JD Supra - Saudi Arabia",
        url="https://www.jdsupra.com/resources/syndication/docsRSSfeed.aspx?ftype=AllContent&premium=1",
        category="regulatory",
        region="KSA",
        description="Legal analysis and alerts on Saudi Arabian law from JD Supra contributors.",
        default_enabled=True,
    ),
    CatalogSource(
        id="jdsupra-me",
        name="JD Supra - Middle East",
        url="https://www.jdsupra.com/resources/syndication/docsRSSfeed.aspx?ftype=CommercialLaw&premium=1",
        category="corporate",
        region="GCC",
        description="Commercial and corporate law updates across the Middle East.",
        default_enabled=True,
    ),
    CatalogSource(
        id="mondaq-ksa",
        name="Mondaq - Saudi Arabia",
        url="https://www.mondaq.com/rss?type=area&content=article&geography=62",
        category="regulatory",
        region="KSA",
        description="Legal and regulatory analysis specific to the Kingdom of Saudi Arabia.",
        default_enabled=True,
    ),
    CatalogSource(
        id="mondaq-uae",
        name="Mondaq - UAE",
        url="https://www.mondaq.com/rss?type=area&content=article&geography=60",
        category="regulatory",
        region="GCC",
        description="Legal and regulatory analysis for the United Arab Emirates.",
        default_enabled=False,
    ),
    CatalogSource(
        id="tamimi",
        name="Al Tamimi & Company",
        url="https://www.tamimi.com/feed/",
        category="corporate",
        region="GCC",
        description="Leading GCC law firm covering Saudi, UAE, and wider Middle East legal developments.",
        default_enabled=True,
    ),
    CatalogSource(
        id="arabnews",
        name="Arab News",
        url="https://www.arabnews.com/rss.xml",
        category="general",
        region="KSA",
        description="Saudi Arabia's first English-language daily, covering legal and business news.",
        default_enabled=True,
    ),
    CatalogSource(
        id="saudigazette",
        name="Saudi Gazette",
        url="https://saudigazette.com.sa/rss",
        category="general",
        region="KSA",
        description="Saudi Gazette English-language news including legal and regulatory updates.",
        default_enabled=True,
    ),
    CatalogSource(
        id="gulfnews",
        name="Gulf News",
        url="https://gulfnews.com/rss",
        category="general",
        region="GCC",
        description="Major GCC publication covering business, legal, and regulatory developments.",
        default_enabled=False,
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
    CatalogSource(
        id="zawya",
        name="Zawya - MENA Legal",
        url="https://www.zawya.com/mena/en/rss.xml",
        category="corporate",
        region="GCC",
        description="MENA business and legal intelligence from Refinitiv/Zawya.",
        default_enabled=False,
    ),
]

_CATALOG_BY_ID: dict[str, CatalogSource] = {s.id: s for s in SOURCE_CATALOG}

CACHE_TTL_SECONDS = 30 * 60  # 30 minutes
HTTP_TIMEOUT = 20.0

# ---------------------------------------------------------------------------
# In-memory cache -- keyed by workspace id for isolation
# ---------------------------------------------------------------------------

_cache: dict[str, dict[str, Any]] = {}


class NewsItem(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    image_url: str | None = None
    source: str
    published_at: str
    category: str


class NewsResponse(BaseModel):
    items: list[NewsItem]
    fetched_at: str
    source_count: int


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

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _extract_image(entry: dict) -> str | None:
    # media_content / media_thumbnail (common in RSS 2.0 + Media RSS)
    for media in entry.get("media_content", []):
        url = media.get("url", "")
        if url and ("image" in media.get("type", "image")):
            return url
    for thumb in entry.get("media_thumbnail", []):
        if thumb.get("url"):
            return thumb["url"]

    # enclosures
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href") or enc.get("url")

    # look in summary/content for <img>
    content = entry.get("summary", "") or ""
    if not content:
        content_list = entry.get("content", [])
        if content_list:
            content = content_list[0].get("value", "")

    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
    if img_match:
        return img_match.group(1)

    return None


def _parse_date(entry: dict) -> str:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                dt = datetime(*parsed[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            return raw
    return datetime.now(timezone.utc).isoformat()


async def _fetch_feed(
    client: httpx.AsyncClient, source: dict[str, str]
) -> list[NewsItem]:
    """Parse a single RSS/Atom feed and return NewsItems."""
    try:
        resp = await client.get(source["url"], follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Feed fetch failed for %s: %s", source["name"], exc)
        return []

    try:
        import xml.etree.ElementTree as ET

        items: list[NewsItem] = []
        root = ET.fromstring(resp.text)

        # Detect feed type
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        atom_entries = root.findall("atom:entry", ns) or root.findall(
            "{http://www.w3.org/2005/Atom}entry"
        )

        if atom_entries:
            for entry_el in atom_entries[:15]:
                title = (
                    entry_el.findtext("{http://www.w3.org/2005/Atom}title", "").strip()
                )
                if not title:
                    continue
                link_el = entry_el.find("{http://www.w3.org/2005/Atom}link")
                link = link_el.get("href", "") if link_el is not None else ""
                summary_el = entry_el.findtext(
                    "{http://www.w3.org/2005/Atom}summary", ""
                ) or entry_el.findtext("{http://www.w3.org/2005/Atom}content", "")
                published = entry_el.findtext(
                    "{http://www.w3.org/2005/Atom}published", ""
                ) or entry_el.findtext("{http://www.w3.org/2005/Atom}updated", "")
                if not published:
                    published = datetime.now(timezone.utc).isoformat()

                img = None
                media_ns = "http://search.yahoo.com/mrss/"
                media_content = entry_el.find(f"{{{media_ns}}}content")
                if media_content is not None:
                    img = media_content.get("url")
                if not img:
                    media_thumb = entry_el.find(f"{{{media_ns}}}thumbnail")
                    if media_thumb is not None:
                        img = media_thumb.get("url")
                if not img:
                    img_match = re.search(
                        r'<img[^>]+src=["\']([^"\']+)', summary_el or ""
                    )
                    if img_match:
                        img = img_match.group(1)

                item_id = hashlib.md5(
                    f"{source['name']}:{link or title}".encode()
                ).hexdigest()
                items.append(
                    NewsItem(
                        id=item_id,
                        title=title,
                        summary=_strip_html(summary_el or "")[:280],
                        url=link,
                        image_url=img,
                        source=source["name"],
                        published_at=published,
                        category=source.get("category", "international"),
                    )
                )
        else:
            # RSS 2.0
            channel = root.find("channel")
            if channel is None:
                channel = root
            for item_el in channel.findall("item")[:15]:
                title = (item_el.findtext("title") or "").strip()
                if not title:
                    continue
                link = (item_el.findtext("link") or "").strip()
                desc = item_el.findtext("description") or ""
                pub_date = (
                    item_el.findtext("pubDate")
                    or item_el.findtext("dc:date")
                    or datetime.now(timezone.utc).isoformat()
                )

                img = None
                for child in item_el:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if tag in ("content", "thumbnail"):
                        img = child.get("url")
                        if img:
                            break
                if not img:
                    enc = item_el.find("enclosure")
                    if enc is not None and enc.get("type", "").startswith("image"):
                        img = enc.get("url")
                if not img:
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)', desc)
                    if img_match:
                        img = img_match.group(1)

                item_id = hashlib.md5(
                    f"{source['name']}:{link or title}".encode()
                ).hexdigest()
                items.append(
                    NewsItem(
                        id=item_id,
                        title=title,
                        summary=_strip_html(desc)[:280],
                        url=link,
                        image_url=img,
                        source=source["name"],
                        published_at=pub_date,
                        category=source.get("category", "international"),
                    )
                )

        return items

    except Exception as exc:
        logger.warning("Feed parse failed for %s: %s", source["name"], exc)
        return []


def _get_enabled_sources(workspace_settings: dict[str, Any] | None) -> list[CatalogSource]:
    """Resolve the active sources for a workspace."""
    if workspace_settings:
        enabled_ids = workspace_settings.get("news_enabled_sources")
        if isinstance(enabled_ids, list) and enabled_ids:
            return [s for s in SOURCE_CATALOG if s.id in enabled_ids]
    return [s for s in SOURCE_CATALOG if s.default_enabled]


async def _aggregate_feeds(sources: list[CatalogSource]) -> list[NewsItem]:
    """Fetch all feeds concurrently, merge, deduplicate, sort by date."""
    feed_dicts = [{"name": s.name, "url": s.url, "category": s.category} for s in sources]

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={
            "User-Agent": "HeyAmin-NewsBot/1.0 (+https://heyamin.com)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    ) as client:
        results = await asyncio.gather(
            *[_fetch_feed(client, src) for src in feed_dicts],
            return_exceptions=True,
        )

    all_items: list[NewsItem] = []
    for result in results:
        if isinstance(result, list):
            all_items.extend(result)

    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in all_items:
        if item.id not in seen:
            seen.add(item.id)
            unique.append(item)

    unique.sort(key=lambda x: x.published_at, reverse=True)
    return unique[:40]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/legal", response_model=NewsResponse)
async def get_legal_news(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
) -> NewsResponse:
    """Aggregated legal news filtered by workspace-enabled sources.

    Cached in-memory per workspace for 30 minutes.
    """
    ws_id = str(ctx.workspace.id) if ctx.workspace else "__default__"
    ws_settings = (ctx.workspace.settings if ctx.workspace and hasattr(ctx.workspace, "settings") else None) or {}

    now = time.time()
    ws_cache = _cache.get(ws_id)
    if ws_cache and ws_cache["items"] and (now - float(ws_cache["fetched_at"])) < CACHE_TTL_SECONDS:
        return NewsResponse(
            items=ws_cache["items"],
            fetched_at=datetime.fromtimestamp(
                float(ws_cache["fetched_at"]), tz=timezone.utc
            ).isoformat(),
            source_count=len(_get_enabled_sources(ws_settings)),
        )

    sources = _get_enabled_sources(ws_settings)
    items = await _aggregate_feeds(sources)
    _cache[ws_id] = {"items": items, "fetched_at": now}

    return NewsResponse(
        items=items,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source_count=len(sources),
    )


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

    # Invalidate cache for this workspace so next fetch uses new sources
    _cache.pop(str(workspace.id), None)

    return await get_news_sources(ctx)
