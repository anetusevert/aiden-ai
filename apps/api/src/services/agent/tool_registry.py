"""Registers all tools available to Amin and provides their OpenAI function schemas."""

from dataclasses import dataclass
from typing import Any, Callable, Coroutine

ROLE_HIERARCHY = {"VIEWER": 0, "EDITOR": 1, "ADMIN": 2}


@dataclass
class ToolResult:
    """Result returned by a tool execution."""

    content: str
    data: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class Tool:
    """Definition of an agent tool."""

    name: str
    description: str
    parameters: dict[str, Any]
    execute: Callable[..., Coroutine[Any, Any, ToolResult]]
    read_only: bool = True
    requires_confirmation: bool = False
    risk_level: str = "low"
    min_role: str = "VIEWER"


class ToolRegistry:
    """Registry of tools available to the Amin agent."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get_all(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_by_name(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_for_role(self, role: str) -> list[Tool]:
        """Get tools accessible to the given role."""
        level = ROLE_HIERARCHY.get(role.upper(), 0)
        return [t for t in self._tools.values() if ROLE_HIERARCHY.get(t.min_role, 0) <= level]

    def get_openai_tools(self, role: str | None = None) -> list[dict[str, Any]]:
        """Get tools in OpenAI function-calling format, optionally filtered by role."""
        tools = self.get_for_role(role) if role else list(self._tools.values())
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]
