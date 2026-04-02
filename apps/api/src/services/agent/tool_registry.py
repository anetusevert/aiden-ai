"""Registers all tools available to Amin and provides their OpenAI function schemas."""

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


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

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Get all tools in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]
