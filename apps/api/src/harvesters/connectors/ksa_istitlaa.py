"""KSA Istitlaa (Public Consultations) connector — draft law signal scraper.

Scrapes the National Competitiveness Center's Istitlaa platform for open and
recent public consultations on draft legislation. Every item is high-importance
as it signals upcoming law changes.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.harvesters.connectors.base import Connector
from src.harvesters.models import ParsedRecord, SourceItem
from src.harvesters.storage import save_artifact

if TYPE_CHECKING:
    from src.harvesters.http import HttpClient

logger = logging.getLogger(__name__)

ISTITLAA_URL = "https://istitlaa.ncc.gov.sa/ar/regulations"
ISTITLAA_BASE = "https://istitlaa.ncc.gov.sa"


def _parse_date(text: str) -> str | None:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return m.group(0)
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        day, month, year = m.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


class KsaIstitlaaConnector(Connector):
    """Connector for Istitlaa public consultations on draft legislation."""

    name = "ksa_istitlaa"
    jurisdiction = "KSA"
    source_name = "Istitlaa Public Consultations"

    _failure_reasons: list[str]

    def __init__(self, http: "HttpClient", out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []

    def list_items(self, limit: int) -> list[SourceItem]:
        if limit < 1:
            return []

        items: list[SourceItem] = []

        try:
            html = self.http.get(ISTITLAA_URL)
            soup = BeautifulSoup(html, "html.parser")

            cards = (
                soup.select(".regulation-card")
                or soup.select("article")
                or soup.select(".card")
                or soup.select("tr")
                or soup.select("[class*='regulation']")
                or soup.select("[class*='consult']")
            )

            if not cards:
                for a in soup.find_all("a", href=True):
                    href = str(a["href"])
                    if "/regulation/" in href.lower() or "/consultation/" in href.lower():
                        title = a.get_text(strip=True)
                        if title and len(title) > 5:
                            full_url = urljoin(ISTITLAA_BASE, href)
                            items.append(
                                SourceItem(
                                    source_url=full_url,
                                    meta={
                                        "connector": self.name,
                                        "title": title,
                                        "importance": "high",
                                    },
                                )
                            )
                            if len(items) >= limit:
                                break
            else:
                for card in cards[:limit]:
                    link_el = card.find("a", href=True)
                    url = ""
                    if link_el:
                        url = urljoin(ISTITLAA_BASE, str(link_el["href"]))

                    title = ""
                    for tag in ["h2", "h3", "h4", "h5", "a"]:
                        el = card.find(tag)
                        if el:
                            title = el.get_text(strip=True)
                            if title and len(title) > 5:
                                break
                    if not title:
                        title = card.get_text(strip=True)[:200]
                    if not title or not url:
                        continue

                    # Look for status (open/closed)
                    status_text = ""
                    for cls in ["status", "badge", "label", "state"]:
                        el = card.find(class_=re.compile(cls, re.I))
                        if el:
                            status_text = el.get_text(strip=True)
                            break

                    # Look for deadline
                    deadline = ""
                    for cls in ["deadline", "date", "end", "expiry"]:
                        el = card.find(class_=re.compile(cls, re.I))
                        if el:
                            deadline = el.get_text(strip=True)
                            break

                    # Look for ministry/agency
                    ministry = ""
                    for cls in ["ministry", "agency", "org", "entity"]:
                        el = card.find(class_=re.compile(cls, re.I))
                        if el:
                            ministry = el.get_text(strip=True)
                            break

                    items.append(
                        SourceItem(
                            source_url=url,
                            meta={
                                "connector": self.name,
                                "title": title,
                                "status": status_text,
                                "consultation_deadline": deadline,
                                "ministry": ministry,
                                "importance": "high",
                            },
                        )
                    )

        except Exception as e:
            logger.warning("Istitlaa listing fetch failed: %s", e)
            self._failure_reasons.append(f"listing_fetch_failed: {type(e).__name__}")

        logger.info("Istitlaa: discovered %d consultations", len(items))
        return items[:limit]

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        logger.info("Istitlaa: fetching consultation %s", item.source_url)

        try:
            html = self.http.get(item.source_url)
        except Exception as e:
            logger.warning("Istitlaa fetch failed: %s", e)
            html = b""
            self._failure_reasons.append(f"detail_fetch_failed: {type(e).__name__}")

        sha256 = hashlib.sha256(html or b"empty").hexdigest()
        artifact_path = str(self.out_dir / f"{sha256}.html")
        if html:
            artifact_path, sha256 = save_artifact(self.out_dir, html, "html")

        title_ar = None
        if html:
            try:
                detail_soup = BeautifulSoup(html, "html.parser")
                for tag in ["h1", "h2", "h3"]:
                    el = detail_soup.find(tag)
                    if el:
                        text = el.get_text(strip=True)
                        if text and any("\u0600" <= c <= "\u06FF" for c in text):
                            title_ar = text
                            break
            except Exception:
                pass

        meta = item.meta or {}
        title = meta.get("title", "")
        if not title_ar and title and any("\u0600" <= c <= "\u06FF" for c in title):
            title_ar = title

        return ParsedRecord(
            jurisdiction=self.jurisdiction,
            source_name=self.source_name,
            source_url=item.source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            title_ar=title_ar,
            title_en=title if title and not any("\u0600" <= c <= "\u06FF" for c in title) else None,
            instrument_type_guess="consultation",
            published_at_guess=_parse_date(meta.get("consultation_deadline", "")),
            raw_artifact_path=artifact_path,
            raw_sha256=sha256,
        )

    def get_failure_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for reason in self._failure_reasons:
            cat = reason.split(":")[0] if ":" in reason else reason
            summary[cat] = summary.get(cat, 0) + 1
        return summary
