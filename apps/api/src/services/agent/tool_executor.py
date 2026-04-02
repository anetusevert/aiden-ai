"""Executes tool calls with concurrent/serial batching.

Pattern extracted from Claude Code's toolOrchestration.ts:
- Read-only tools run concurrently via asyncio.gather()
- Mutating tools run serially in order
- Combined results returned in original call order
"""

import asyncio
import json
import logging
from typing import Any

from src.services.agent.tool_registry import Tool, ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


async def execute_tool_calls(
    tool_calls: list[Any],
    registry: ToolRegistry,
    context: dict[str, Any],
) -> list[ToolResult]:
    """Execute tool calls with concurrent/serial batching.

    Partitions calls into read_only (concurrent) and mutating (serial),
    then runs them accordingly. Returns results in original call order.
    """
    parsed = _parse_calls(tool_calls)
    if not parsed:
        return []

    read_only_calls: list[tuple[int, str, dict[str, Any]]] = []
    mutating_calls: list[tuple[int, str, dict[str, Any]]] = []

    for idx, (name, args) in enumerate(parsed):
        tool = registry.get_by_name(name)
        if tool is None:
            mutating_calls.append((idx, name, args))
            continue
        if tool.read_only:
            read_only_calls.append((idx, name, args))
        else:
            mutating_calls.append((idx, name, args))

    results: dict[int, ToolResult] = {}

    # Run read-only calls concurrently
    if read_only_calls:
        async def _run_ro(item: tuple[int, str, dict[str, Any]]) -> tuple[int, ToolResult]:
            idx, name, args = item
            return idx, await _execute_single(name, args, registry, context)

        concurrent_results = await asyncio.gather(
            *(_run_ro(c) for c in read_only_calls),
            return_exceptions=False,
        )
        for idx, result in concurrent_results:
            results[idx] = result

    # Run mutating calls serially
    for idx, name, args in mutating_calls:
        results[idx] = await _execute_single(name, args, registry, context)

    return [results[i] for i in sorted(results.keys())]


async def _execute_single(
    name: str,
    args: dict[str, Any],
    registry: ToolRegistry,
    context: dict[str, Any],
) -> ToolResult:
    """Execute a single tool call."""
    tool = registry.get_by_name(name)
    if tool is None:
        return ToolResult(content="", error=f"Unknown tool: {name}")

    try:
        return await tool.execute(args, context)
    except Exception as e:
        logger.error("Tool %s failed: %s", name, e, exc_info=True)
        return ToolResult(content="", error=f"Tool execution failed: {e}")


def _parse_calls(tool_calls: list[Any]) -> list[tuple[str, dict[str, Any]]]:
    """Parse raw OpenAI tool_calls into (name, args) tuples."""
    parsed: list[tuple[str, dict[str, Any]]] = []
    for tc in tool_calls:
        try:
            name = tc.function.name
            raw_args = tc.function.arguments
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            parsed.append((name, args))
        except Exception as e:
            logger.warning("Failed to parse tool call: %s", e)
            parsed.append(("_parse_error", {}))
    return parsed
