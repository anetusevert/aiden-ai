"""KSA Saudi Press Agency (SPA) connector — RSS-based legal news scraper.

Fetches from the SPA public RSS feeds (Politics and Economy), filters for
legally relevant items using keyword matching, and assigns importance.
"""

from __future__ import annotations

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from src.harvesters.connectors.base import Connector
from src.harvesters.models import ParsedRecord, SourceItem
from src.harvesters.storage import save_artifact

if TYPE_CHECKING:
    from src.harvesters.http import HttpClient

logger = logging.getLogger(__name__)

SPA_FEEDS = [
    "https://www.spa.gov.sa/en/rss/category/Politics",
    "https://www.spa.gov.sa/en/rss/category/Economy",
]

LEGAL_KEYWORDS_RE = re.compile(
    r"\b(law|regulation|decree|ministry|cabinet|royal|compliance|penalty|fine"
    r"|legislation|judicial|court|amendment|circular)\b",
    re.IGNORECASE,
)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(raw: str) -> str:
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", raw)).strip()


class KsaSpaConnector(Connector):
    """Connector for Saudi Press Agency RSS feeds filtered for legal relevance."""

    name = "ksa_spa"
    jurisdiction = "KSA"
    source_name = "Saudi Press Agency"

    _failure_reasons: list[str]

    def __init__(self, http: "HttpClient", out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []

    def list_items(self, limit: int) -> list[SourceItem]:
        if limit < 1:
            return []

        seen_urls: set[str] = set()
        items: list[SourceItem] = []

        for feed_url in SPA_FEEDS:
            if len(items) >= limit:
                break
            try:
                raw = self.http.get(feed_url)
                root = ET.fromstring(raw)
                channel = root.find("channel")
                if channel is None:
                    channel = root

                for item_el in channel.findall("item"):
                    if len(items) >= limit:
                        break

                    title = (item_el.findtext("title") or "").strip()
                    link = (item_el.findtext("link") or "").strip()
                    desc = item_el.findtext("description") or ""

                    if not title or not link:
                        continue
                    if link in seen_urls:
                        continue

                    text = f"{title} {desc}"
                    if not LEGAL_KEYWORDS_RE.search(text):
                        continue

                    seen_urls.add(link)

                    pub_date = (
                        item_el.findtext("pubDate")
                        or datetime.now(timezone.utc).isoformat()
                    )

                    # Extract image from media:content or enclosure
                    image_url = None
                    for child in item_el:
                        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        if tag in ("content", "thumbnail"):
                            image_url = child.get("url")
                            if image_url:
                                break
                    if not image_url:
                        enc = item_el.find("enclosure")
                        if enc is not None and enc.get("type", "").startswith("image"):
                            image_url = enc.get("url")

                    importance = "normal"
                    title_lower = title.lower()
                    if "royal decree" in title_lower or "cabinet" in title_lower:
                        importance = "high"

                    items.append(
                        SourceItem(
                            source_url=link,
                            meta={
                                "connector": self.name,
                                "title": title,
                                "summary": _strip_html(desc)[:500],
                                "published_at": pub_date,
                                "image_url": image_url,
                                "importance": importance,
                            },
                        )
                    )
            except Exception as e:
                logger.warning("SPA feed fetch failed for %s: %s", feed_url, e)
                self._failure_reasons.append(f"feed_fetch_failed: {type(e).__name__}")

        logger.info("SPA: discovered %d legally relevant items", len(items))
        return items

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        logger.info("SPA: fetching article %s", item.source_url)

        try:
            html = self.http.get(item.source_url)
        except Exception as e:
            logger.warning("SPA article fetch failed: %s", e)
            html = b""
            self._failure_reasons.append(f"article_fetch_failed: {type(e).__name__}")

        sha256 = hashlib.sha256(html or b"empty").hexdigest()
        artifact_path = str(self.out_dir / f"{sha256}.html")
        if html:
            raw_path, sha256 = save_artifact(self.out_dir, html, "html")
            artifact_path = raw_path

        meta = item.meta or {}
        return ParsedRecord(
            jurisdiction=self.jurisdiction,
            source_name=self.source_name,
            source_url=item.source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            title_ar=None,
            title_en=meta.get("title"),
            instrument_type_guess="news",
            published_at_guess=None,
            raw_artifact_path=artifact_path,
            raw_sha256=sha256,
        )

    def get_failure_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for reason in self._failure_reasons:
            cat = reason.split(":")[0] if ":" in reason else reason
            summary[cat] = summary.get(cat, 0) + 1
        return summary
