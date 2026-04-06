"""Connectors for various GCC legal source websites.

Each connector implements the Connector interface to scrape
a specific jurisdiction's legal document repository.
"""

from __future__ import annotations

from src.harvesters.connectors.base import BaseConnector, Connector

_CONNECTOR_REGISTRY: dict[str, type[Connector]] = {}


def register(connector_cls: type[Connector]) -> type[Connector]:
    """Register a connector class in the registry."""
    name = getattr(connector_cls, "name", None)
    if not name:
        raise ValueError(f"Connector class {connector_cls.__name__} must have a 'name' attribute")

    if name in _CONNECTOR_REGISTRY:
        raise ValueError(
            f"Connector name '{name}' is already registered by {_CONNECTOR_REGISTRY[name].__name__}"
        )

    _CONNECTOR_REGISTRY[name] = connector_cls
    return connector_cls


def get_connector(name: str) -> type[Connector]:
    """Get a connector class by name."""
    if name not in _CONNECTOR_REGISTRY:
        available = ", ".join(sorted(_CONNECTOR_REGISTRY.keys())) or "(none)"
        raise KeyError(
            f"Unknown connector: '{name}'. Available connectors: {available}"
        )

    return _CONNECTOR_REGISTRY[name]


def list_connectors() -> list[str]:
    """List all registered connector names."""
    return sorted(_CONNECTOR_REGISTRY.keys())


from src.harvesters.connectors.ksa_boe import KsaBoeConnector
from src.harvesters.connectors.ksa_istitlaa import KsaIstitlaaConnector
from src.harvesters.connectors.ksa_misa import KsaMisaConnector
from src.harvesters.connectors.ksa_moj import KsaMojConnector
from src.harvesters.connectors.ksa_sba import KsaSbaConnector
from src.harvesters.connectors.ksa_sjp import KsaSjpConnector
from src.harvesters.connectors.ksa_spa import KsaSpaConnector
from src.harvesters.connectors.ksa_uaq import KsaUaqConnector
from src.harvesters.connectors.qatar_almeezan import QatarAlmeezanConnector
from src.harvesters.connectors.uae_moj import UaeMojConnector

register(KsaBoeConnector)
register(KsaIstitlaaConnector)
register(KsaMisaConnector)
register(KsaMojConnector)
register(KsaSbaConnector)
register(KsaSjpConnector)
register(KsaSpaConnector)
register(KsaUaqConnector)
register(UaeMojConnector)
register(QatarAlmeezanConnector)

__all__ = [
    "Connector",
    "BaseConnector",
    "KsaBoeConnector",
    "KsaIstitlaaConnector",
    "KsaMisaConnector",
    "KsaMojConnector",
    "KsaSbaConnector",
    "KsaSjpConnector",
    "KsaSpaConnector",
    "KsaUaqConnector",
    "UaeMojConnector",
    "QatarAlmeezanConnector",
    "register",
    "get_connector",
    "list_connectors",
]
