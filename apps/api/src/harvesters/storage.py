"""Storage utilities for persisting harvested data."""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterator

_HASH_BUFFER_SIZE = 65536


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hash of byte data."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file using buffered reading."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(_HASH_BUFFER_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _sanitize_ext(ext: str) -> str:
    """Sanitize file extension to alphanumeric only."""
    ext = ext.lstrip(".")
    sanitized = re.sub(r"[^a-zA-Z0-9]", "", ext)
    return sanitized.lower() if sanitized else "bin"


def save_artifact(out_dir: Path, data: bytes, ext: str) -> tuple[str, str]:
    """Save a raw artifact using content-addressed storage.

    Returns:
        Tuple of (relative_path_posix, sha256_hex).
    """
    if "/" in ext or "\\" in ext:
        raise ValueError("Extension cannot contain path separators")

    sha256_hex = compute_sha256(data)
    safe_ext = _sanitize_ext(ext)

    out_dir = Path(out_dir)
    raw_dir = out_dir / "raw"
    filename = f"{sha256_hex}.{safe_ext}"
    artifact_path = raw_dir / filename

    raw_dir.mkdir(parents=True, exist_ok=True)

    if not artifact_path.exists():
        artifact_path.write_bytes(data)

    relative_path = f"raw/{filename}"
    return relative_path, sha256_hex


def atomic_replace(src: Path, dst: Path) -> None:
    """Atomically replace dst with src using os.replace."""
    os.replace(src, dst)


class StorageManager:
    """Manages storage of harvested records and artifacts."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = Path(base_path)
        self.records_path = self.base_path / "records"
        self.artifacts_path = self.base_path / "artifacts"

    def ensure_directories(self) -> None:
        """Create required storage directories if they don't exist."""
        self.records_path.mkdir(parents=True, exist_ok=True)
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

    def write_record(self, connector: str, record: dict[str, Any]) -> None:
        """Append a single record to the connector's JSONL file."""
        output_file = self.records_path / f"{connector}.jsonl"
        with output_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_records(self, connector: str) -> Iterator[dict[str, Any]]:
        """Read all records from a connector's JSONL file."""
        input_file = self.records_path / f"{connector}.jsonl"
        if not input_file.exists():
            return
        with input_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
