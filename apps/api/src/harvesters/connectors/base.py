"""Base connector interface for legal source scrapers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from src.harvesters.models import ParsedRecord, SourceItem

if TYPE_CHECKING:
    from src.harvesters.http import HttpClient


class Connector(ABC):
    """Abstract base class for jurisdiction-specific connectors.

    Subclasses must implement list_items() and fetch_and_parse() methods
    to discover and harvest documents from their respective legal sources.
    """

    name: str = ""
    jurisdiction: str = ""
    source_name: str = ""

    def __init__(self, http: HttpClient, out_dir: Path) -> None:
        self.http = http
        self.out_dir = Path(out_dir)

    @abstractmethod
    def list_items(self, limit: int) -> list[SourceItem]:
        """Discover items to harvest from the source."""
        raise NotImplementedError

    @abstractmethod
    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        """Fetch and parse a single source item."""
        raise NotImplementedError


BaseConnector = Connector
