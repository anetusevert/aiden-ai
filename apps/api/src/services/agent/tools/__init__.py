"""Amin agent tools — auto-discovery from this package.

Every module in this package that exposes `Tool` instances at module level
is automatically registered. No manual imports needed when adding new tools.
"""

import importlib
import logging
import pkgutil
from pathlib import Path

from src.services.agent.tool_registry import Tool, ToolRegistry

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).parent


def register_all_tools(registry: ToolRegistry) -> None:
    """Scan this package and register every Tool instance found."""
    for module_info in pkgutil.iter_modules([str(_PACKAGE_DIR)]):
        if module_info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{__name__}.{module_info.name}")
        except Exception:
            logger.warning("Failed to import tool module %s", module_info.name, exc_info=True)
            continue

        for attr_name in dir(mod):
            obj = getattr(mod, attr_name, None)
            if isinstance(obj, Tool):
                registry.register(obj)

    logger.info("Registered %d tools via auto-discovery", len(registry.get_all()))
