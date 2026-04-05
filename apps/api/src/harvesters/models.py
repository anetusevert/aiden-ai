"""Data models for harvested records.

This module contains Pydantic models for validating the JSONL output contract.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SourceItem(BaseModel):
    """Represents an item discovered by a connector's list_items method.

    This is the intermediate data structure passed from list_items() to fetch_and_parse().
    """

    source_url: Annotated[str, Field(min_length=1, description="URL to fetch")]
    meta: dict[str, Any] | None = Field(default=None, description="Optional metadata about the item")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: str) -> str:
        """Validate source_url starts with http:// or https://."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("source_url must start with http:// or https://")
        return v


class ParsedRecord(BaseModel):
    """Pydantic model for validating harvested legal document records.

    Validates the JSONL output contract with strict field requirements.
    """

    jurisdiction: Annotated[str, Field(min_length=1, description="Jurisdiction code (uppercase letters/numbers/underscore)")]
    source_name: Annotated[str, Field(min_length=1, description="Source name")]
    source_url: Annotated[str, Field(min_length=1, description="Source URL (must start with http:// or https://)")]
    retrieved_at: Annotated[str, Field(min_length=1, description="ISO 8601 datetime with timezone")]
    title_ar: str | None = Field(default=None, description="Arabic title (optional)")
    title_en: str | None = Field(default=None, description="English title (optional)")
    instrument_type_guess: str | None = Field(default=None, description="Guessed instrument type (optional)")
    published_at_guess: str | None = Field(default=None, description="Guessed publication date YYYY-MM-DD (optional)")
    raw_artifact_path: Annotated[str, Field(min_length=1, description="Path to raw artifact")]
    raw_sha256: Annotated[str, Field(min_length=64, max_length=64, description="SHA256 hash (64 lowercase hex chars)")]

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        """Validate jurisdiction is uppercase letters, numbers, or underscores only."""
        if not re.match(r"^[A-Z0-9_]+$", v):
            raise ValueError("jurisdiction must contain only uppercase letters, numbers, or underscores (e.g., 'KSA')")
        return v

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: str) -> str:
        """Validate source_url starts with http:// or https://."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("source_url must start with http:// or https://")
        return v

    @field_validator("retrieved_at")
    @classmethod
    def validate_retrieved_at(cls, v: str) -> str:
        """Validate retrieved_at is ISO 8601 with timezone info."""
        try:
            dt = datetime.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"retrieved_at must be valid ISO 8601 datetime: {e}")

        if dt.tzinfo is None:
            raise ValueError("retrieved_at must include timezone offset (e.g., '+00:00' or 'Z')")
        return v

    @field_validator("title_ar")
    @classmethod
    def validate_title_ar(cls, v: str | None) -> str | None:
        """Validate title_ar is non-empty after strip if present."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("title_ar must be non-empty after stripping whitespace if provided")
            return stripped
        return v

    @field_validator("title_en")
    @classmethod
    def validate_title_en(cls, v: str | None) -> str | None:
        """Validate title_en is non-empty after strip if present."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("title_en must be non-empty after stripping whitespace if provided")
            return stripped
        return v

    @field_validator("published_at_guess")
    @classmethod
    def validate_published_at_guess(cls, v: str | None) -> str | None:
        """Validate published_at_guess is YYYY-MM-DD and a valid date if present."""
        if v is not None:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                raise ValueError("published_at_guess must be in YYYY-MM-DD format")
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"published_at_guess '{v}' is not a valid date")
        return v

    @field_validator("raw_sha256")
    @classmethod
    def validate_raw_sha256(cls, v: str) -> str:
        """Validate raw_sha256 is exactly 64 lowercase hex characters."""
        if not re.match(r"^[a-f0-9]{64}$", v):
            raise ValueError("raw_sha256 must be exactly 64 lowercase hex characters")
        return v


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL file and return list of dictionaries."""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def validate_jsonl(path: Path) -> tuple[list[ParsedRecord], list[tuple[int, str]]]:
    """Validate JSONL file against ParsedRecord schema."""
    valid_records: list[ParsedRecord] = []
    errors: list[tuple[int, str]] = []

    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as e:
                errors.append((line_num, f"Invalid JSON: {e}"))
                continue

            try:
                record = ParsedRecord.model_validate(data)
                valid_records.append(record)
            except Exception as e:
                error_msg = str(e)
                if hasattr(e, "errors"):
                    error_details = []
                    for err in e.errors():  # noqa: PGH003
                        field = ".".join(str(loc) for loc in err.get("loc", []))
                        msg = err.get("msg", str(err))
                        error_details.append(f"{field}: {msg}")
                    error_msg = "; ".join(error_details)
                errors.append((line_num, error_msg))

    return valid_records, errors


class PreviousRecordInfo:
    """Lightweight container for previous record comparison data."""

    __slots__ = ("raw_sha256", "title_ar", "title_en", "published_at_guess")

    def __init__(self, raw_sha256: str, title_ar: str | None, title_en: str | None, published_at_guess: str | None) -> None:
        self.raw_sha256 = raw_sha256
        self.title_ar = title_ar
        self.title_en = title_en
        self.published_at_guess = published_at_guess


def load_previous_records_map(path: Path) -> dict[str, PreviousRecordInfo]:
    """Load previous JSONL records into a lookup map keyed by source_url."""
    if not path.exists():
        return {}

    result: dict[str, PreviousRecordInfo] = {}
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    data = json.loads(stripped)
                    source_url = data.get("source_url")
                    raw_sha256 = data.get("raw_sha256")
                    if source_url and raw_sha256:
                        result[source_url] = PreviousRecordInfo(
                            raw_sha256=raw_sha256,
                            title_ar=data.get("title_ar"),
                            title_en=data.get("title_en"),
                            published_at_guess=data.get("published_at_guess"),
                        )
                except json.JSONDecodeError:
                    continue
    except (OSError, IOError):
        return {}

    return result
