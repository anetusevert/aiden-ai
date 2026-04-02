"""Loads and caches Amin's Soul files from amin-soul/ directory."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_soul_dir() -> Path:
    """Locate the amin-soul/ directory.

    Checks, in order:
    1. AMIN_SOUL_DIR env var (explicit override)
    2. /app/amin-soul (Docker mount)
    3. Walk up from this file until amin-soul/ is found
    """
    env_dir = os.environ.get("AMIN_SOUL_DIR")
    if env_dir:
        return Path(env_dir)

    docker_path = Path("/app/amin-soul")
    if docker_path.is_dir():
        return docker_path

    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "amin-soul"
        if candidate.is_dir():
            return candidate

    logger.warning("Could not locate amin-soul/ directory, using fallback")
    return Path(__file__).resolve().parent / "amin-soul"


SOUL_DIR = _find_soul_dir()

_cache: dict[str, str] | None = None

SOUL_FILES = ["SOUL.md", "IDENTITY.md", "AGENTS.md", "STYLE.md", "HEARTBEAT.md"]


def load_soul_files() -> dict[str, str]:
    """Read all soul files from amin-soul/ directory.

    Results are cached at module level so files are only read once.
    """
    global _cache
    if _cache is not None:
        return _cache

    result: dict[str, str] = {}
    for filename in SOUL_FILES:
        path = SOUL_DIR / filename
        if path.exists():
            result[filename] = path.read_text(encoding="utf-8")
        else:
            logger.warning("Soul file not found: %s", path)
            result[filename] = ""

    _cache = result
    return result


def get_soul_system_prompt() -> str:
    """Concatenate all soul files into a single system prompt block."""
    files = load_soul_files()
    sections: list[str] = []
    for filename in SOUL_FILES:
        content = files.get(filename, "")
        if content:
            sections.append(content)
    return "\n\n---\n\n".join(sections)
