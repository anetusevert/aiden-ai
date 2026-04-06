"""Unified news service — fetch, persist, classify, summarise, and wiki-file.

Replaces the inline aggregation logic in the news router with a persistent
pipeline that survives restarts and feeds both the API and the wiki.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm import get_llm_provider
from src.models.news_item import NewsItem

logger = logging.getLogger(__name__)

# A deterministic system-level user ID for automated operations
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"

# RSS feed timeout
_HTTP_TIMEOUT = 20.0

# Max GPT calls per fetch cycle (rate limiter)
_MAX_GPT_CALLS_PER_CYCLE = 10

# ── importance keyword lists ────────────────────────────────────────────

_HIGH_KEYWORDS = [
    "royal decree", "cabinet decision", "new law", "regulation", "circular",
    "amendment", "penalty", "fine", "compliance deadline", "effective date",
    "consultation", "istitlaa", "bar association", "decree", "ruling",
    "enforcement", "license suspension", "sanctions",
]

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(raw: str) -> str:
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", raw)).strip()


def _make_external_id(source_name: str, url: str) -> str:
    """MD5 hash of (source_name + url) — dedup key."""
    return hashlib.md5(f"{source_name}:{url}".encode()).hexdigest()


def classify_importance(
    title: str,
    summary: str | None,
    source_category: str,
) -> str:
    """Rule-based importance classification — no GPT call needed."""
    text = f"{title} {summary or ''}".lower()
    if any(kw in text for kw in _HIGH_KEYWORDS):
        return "high"
    if source_category in ("legislation", "jurisprudence", "consultation", "tax_law", "financial_regulation"):
        return "high"
    return "normal"


# ── RSS feed fetching (migrated from router) ────────────────────────────


async def _fetch_rss_feed(
    client: httpx.AsyncClient,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    """Parse a single RSS/Atom feed and return raw item dicts."""
    try:
        resp = await client.get(source["url"], follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Feed fetch failed for %s: %s", source["name"], exc)
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as exc:
        logger.warning("Feed parse failed for %s: %s", source["name"], exc)
        return []

    items: list[dict[str, Any]] = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    atom_entries = root.findall("{http://www.w3.org/2005/Atom}entry")

    if atom_entries:
        for entry_el in atom_entries[:20]:
            title = entry_el.findtext("{http://www.w3.org/2005/Atom}title", "").strip()
            if not title:
                continue
            link_el = entry_el.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
            summary_text = (
                entry_el.findtext("{http://www.w3.org/2005/Atom}summary", "")
                or entry_el.findtext("{http://www.w3.org/2005/Atom}content", "")
            )
            published = (
                entry_el.findtext("{http://www.w3.org/2005/Atom}published", "")
                or entry_el.findtext("{http://www.w3.org/2005/Atom}updated", "")
            )

            img = None
            media_ns = "http://search.yahoo.com/mrss/"
            mc = entry_el.find(f"{{{media_ns}}}content")
            if mc is not None:
                img = mc.get("url")
            if not img:
                mt = entry_el.find(f"{{{media_ns}}}thumbnail")
                if mt is not None:
                    img = mt.get("url")
            if not img:
                m = re.search(r'<img[^>]+src=["\']([^"\']+)', summary_text or "")
                if m:
                    img = m.group(1)

            items.append({
                "title": title,
                "summary": _strip_html(summary_text or "")[:500],
                "url": link,
                "image_url": img,
                "source_name": source["name"],
                "source_category": source.get("category", "analysis"),
                "jurisdiction": source.get("region", "GCC"),
                "published_at": published or datetime.now(timezone.utc).isoformat(),
            })
    else:
        channel = root.find("channel")
        if channel is None:
            channel = root
        for item_el in channel.findall("item")[:20]:
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
                m = re.search(r'<img[^>]+src=["\']([^"\']+)', desc)
                if m:
                    img = m.group(1)

            items.append({
                "title": title,
                "summary": _strip_html(desc)[:500],
                "url": link,
                "image_url": img,
                "source_name": source["name"],
                "source_category": source.get("category", "analysis"),
                "jurisdiction": source.get("region", "GCC"),
                "published_at": pub_date,
            })

    return items


def _parse_published_at(raw: str) -> datetime:
    """Best-effort parse of various date formats into timezone-aware datetime."""
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(raw.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    return datetime.now(timezone.utc)


# ── Main service functions ──────────────────────────────────────────────


async def fetch_and_persist_news(db: AsyncSession) -> int:
    """Fetch from all active sources, persist new items, return count of new items."""

    all_raw_items: list[dict[str, Any]] = []

    # Step 1: Fetch RSS catalog sources
    from src.routers.news import SOURCE_CATALOG

    feed_dicts = [
        {"name": s.name, "url": s.url, "category": s.category, "region": s.region}
        for s in SOURCE_CATALOG
        if s.default_enabled
    ]

    async with httpx.AsyncClient(
        timeout=_HTTP_TIMEOUT,
        headers={
            "User-Agent": "HeyAmin-NewsBot/1.0 (+https://heyamin.com)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    ) as client:
        tasks = [_fetch_rss_feed(client, src) for src in feed_dicts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_raw_items.extend(result)

    # Step 2: Fetch from harvester connectors (news-oriented ones)
    from src.harvesters.connectors import get_connector
    from src.harvesters.http import HttpClient

    news_connectors = ["ksa_spa", "ksa_sba", "ksa_misa", "ksa_istitlaa", "ksa_sjp"]

    for connector_name in news_connectors:
        try:
            connector_cls = get_connector(connector_name)
            tmp_dir = Path(tempfile.mkdtemp(prefix=f"news_{connector_name}_"))
            http_client = HttpClient(rate=0.5, retries=2, cache_dir=None)
            connector = connector_cls(http=http_client, out_dir=tmp_dir)

            source_items = await asyncio.to_thread(connector.list_items, 20)
            for si in source_items:
                meta = si.meta or {}
                all_raw_items.append({
                    "title": meta.get("title", si.source_url),
                    "summary": meta.get("summary", ""),
                    "url": si.source_url,
                    "image_url": meta.get("image_url"),
                    "source_name": connector.source_name,
                    "source_category": meta.get("source_category", _connector_category(connector_name)),
                    "jurisdiction": connector.jurisdiction,
                    "published_at": meta.get("published_at", datetime.now(timezone.utc).isoformat()),
                    "importance_hint": meta.get("importance"),
                    "title_ar": meta.get("title_ar"),
                    "consultation_deadline": meta.get("consultation_deadline"),
                })
        except Exception as e:
            logger.warning("News connector %s failed: %s", connector_name, e)

    # Step 3: Persist new items
    new_count = 0
    gpt_calls = 0

    for raw in all_raw_items:
        url = raw.get("url", "")
        source_name = raw.get("source_name", "")
        title = raw.get("title", "")
        if not url or not title:
            continue

        external_id = _make_external_id(source_name, url)

        existing = await db.execute(
            select(NewsItem).where(NewsItem.external_id == external_id)
        )
        if existing.scalar_one_or_none() is not None:
            continue

        source_category = raw.get("source_category", "news")
        summary = raw.get("summary", "")
        importance = raw.get("importance_hint") or classify_importance(title, summary, source_category)
        published_at = _parse_published_at(raw.get("published_at", ""))

        item = NewsItem(
            external_id=external_id,
            title=title[:1000],
            title_ar=(raw.get("title_ar") or "")[:1000] or None,
            summary=summary[:500] if summary else None,
            url=url[:2000],
            image_url=(raw.get("image_url") or "")[:2000] or None,
            source_name=source_name[:200],
            source_category=source_category[:100],
            jurisdiction=raw.get("jurisdiction", "GCC")[:50],
            published_at=published_at,
            importance=importance,
            tags=[],
        )
        db.add(item)
        await db.flush()

        # Generate Amin significance summary for high-importance items
        if importance == "high" and gpt_calls < _MAX_GPT_CALLS_PER_CYCLE:
            try:
                amin_text = await _generate_amin_significance(item)
                item.amin_summary = amin_text[:500] if amin_text else None
                gpt_calls += 1
            except Exception as e:
                logger.warning("Amin summary generation failed for %s: %s", item.id, e)

        new_count += 1

    await db.commit()
    return new_count


async def _generate_amin_significance(item: NewsItem) -> str | None:
    """Ask GPT to write 1 sentence on why this matters to a KSA lawyer."""
    llm = get_llm_provider()
    prompt = (
        f"You are Amin, a GCC legal AI. In ONE sentence, explain why this news item "
        f"is significant for a practicing KSA lawyer. Be specific and practical.\n"
        f"Title: {item.title}\n"
        f"Summary: {item.summary or '(no summary)'}\n"
        f"Source: {item.source_name} ({item.source_category})\n"
        f"Return only the sentence. No preamble."
    )
    try:
        response = await llm.generate(
            prompt,
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=100,
        )
        return response.text.strip()
    except Exception as e:
        logger.warning("LLM significance call failed: %s", e)
        return None


def _connector_category(connector_name: str) -> str:
    """Map connector names to source_category values."""
    mapping = {
        "ksa_spa": "news",
        "ksa_sba": "professional",
        "ksa_misa": "business_law",
        "ksa_istitlaa": "consultation",
        "ksa_sjp": "jurisprudence",
    }
    return mapping.get(connector_name, "news")


# ── Wiki filing pipeline ────────────────────────────────────────────────


async def file_high_importance_to_wiki(db: AsyncSession) -> int:
    """Auto-file high-importance news items to the wiki. Called after fetch cycle."""
    from src.services.wiki_service import WikiService

    items_result = await db.execute(
        select(NewsItem)
        .where(NewsItem.importance == "high")
        .where(NewsItem.wiki_filed.is_(False))
        .where(
            NewsItem.source_category.in_(
                ["legislation", "jurisprudence", "consultation", "tax_law", "financial_regulation"]
            )
        )
        .order_by(NewsItem.published_at.desc())
        .limit(5)
    )
    items = list(items_result.scalars().all())

    if not items:
        return 0

    wiki = WikiService(db=db)
    filed_count = 0

    for item in items:
        try:
            source_text = (
                f"# {item.title}\n\n"
                f"{item.summary or ''}\n\n"
                f"Source: {item.source_name}\n"
                f"URL: {item.url}"
            )
            source_type = "scraped_law" if item.source_category == "legislation" else "news_item"

            result = await wiki.ingest_source(
                source_text=source_text,
                source_title=item.title,
                source_type=source_type,
                org_id=None,
                user_id=SYSTEM_USER_ID,
                metadata={
                    "jurisdiction": item.jurisdiction,
                    "url": item.url,
                    "source": item.source_name,
                    "published_at": item.published_at.isoformat(),
                    "category": item.source_category,
                },
            )
            item.wiki_filed = True
            item.wiki_page_slug = result.primary_page.slug
            await db.flush()
            filed_count += 1
        except Exception as e:
            logger.warning("Wiki filing failed for news item %s: %s", item.id, e)

    await db.commit()
    return filed_count
