"""Multi-agent sub-task forking and parallel execution.

Detects when a user request contains multiple independent sub-tasks,
forks them into parallel executions, and merges the results.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from src.services.agent.llm_router import chat_completion
from src.services.agent.tool_executor import execute_tool_calls
from src.services.agent.tool_registry import Tool, ToolRegistry

logger = logging.getLogger(__name__)

DETECTION_PROMPT = """\
You are analyzing a user's message to determine if it contains multiple independent tasks
that can be executed in parallel.

Available tools: {tool_names}

User message: "{user_message}"

Analyze whether this message contains 2 or more INDEPENDENT sub-tasks that can be worked on
simultaneously. Tasks are independent if they don't depend on each other's results.

If you find parallelizable tasks, return a JSON array of objects:
[
  {{"description": "brief task description", "tools": ["tool_name1"], "context": "relevant context from the message"}},
  ...
]

If the message is a single task or the tasks are sequential/dependent, return: null

Return ONLY valid JSON (array or null), no explanation.\
"""


@dataclass
class SubTask:
    description: str
    tools: list[str]
    context: str


@dataclass
class SubTaskResult:
    description: str
    content: str
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class SubAgentRunner:
    """Detects, forks, and runs parallel sub-tasks."""

    @staticmethod
    async def detect_subtasks(
        user_message: str,
        tools: list[Tool],
    ) -> list[SubTask] | None:
        """Use LLM to detect if a message contains parallelizable sub-tasks.

        Returns a list of SubTask objects if parallel work is possible,
        or None if the message should be handled sequentially.
        """
        if len(user_message.split()) < 8:
            return None

        tool_names = ", ".join(t.name for t in tools)

        try:
            response = await chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a task decomposition engine. Return only valid JSON.",
                    },
                    {
                        "role": "user",
                        "content": DETECTION_PROMPT.format(
                            tool_names=tool_names,
                            user_message=user_message[:1000],
                        ),
                    },
                ],
                tools=None,
                model="gpt-4o-mini",
            )

            raw = (response.choices[0].message.content or "").strip()
            if not raw or raw == "null":
                return None

            # Clean markdown fences
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            parsed = json.loads(raw)
            if not isinstance(parsed, list) or len(parsed) < 2:
                return None

            subtasks = []
            for item in parsed[:4]:  # Cap at 4 parallel tasks
                subtasks.append(SubTask(
                    description=item.get("description", "Sub-task"),
                    tools=item.get("tools", []),
                    context=item.get("context", ""),
                ))
            return subtasks

        except Exception as e:
            logger.warning("Sub-task detection failed: %s", e)
            return None

    @staticmethod
    async def run_subtask(
        subtask: SubTask,
        system_prompt: str,
        registry: ToolRegistry,
        context: dict[str, Any],
    ) -> SubTaskResult:
        """Run a single sub-task with its own tool-calling loop."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Focus on this specific task: {subtask.description}\n\n"
                    f"Context: {subtask.context}\n\n"
                    f"Use the available tools as needed. Be thorough and cite sources."
                ),
            },
        ]

        available_tools = []
        for name in subtask.tools:
            tool = registry.get_by_name(name)
            if tool:
                available_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                })

        all_tools = available_tools or registry.get_openai_tools()
        tool_results_collected: list[dict[str, Any]] = []

        for _round in range(3):  # Max 3 tool rounds per subtask
            response = await chat_completion(
                messages=messages,
                tools=all_tools,
            )
            choice = response.choices[0]
            msg = choice.message

            if not msg.tool_calls:
                return SubTaskResult(
                    description=subtask.description,
                    content=msg.content or "",
                    tool_results=tool_results_collected,
                )

            tc_data = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
            messages.append({"role": "assistant", "tool_calls": tc_data})

            results = await execute_tool_calls(
                msg.tool_calls, registry, context
            )
            for tc, tr in zip(msg.tool_calls, results):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tr.error or tr.content,
                })
                tool_results_collected.append({
                    "tool": tc.function.name,
                    "result": tr.content[:200],
                })

        # Final synthesis after tool rounds
        response = await chat_completion(messages=messages, tools=None)
        return SubTaskResult(
            description=subtask.description,
            content=response.choices[0].message.content or "",
            tool_results=tool_results_collected,
        )

    @staticmethod
    async def run_parallel(
        subtasks: list[SubTask],
        system_prompt: str,
        registry: ToolRegistry,
        context: dict[str, Any],
    ) -> list[SubTaskResult]:
        """Run multiple sub-tasks concurrently."""
        tasks = [
            SubAgentRunner.run_subtask(st, system_prompt, registry, context)
            for st in subtasks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final: list[SubTaskResult] = []
        for st, r in zip(subtasks, results):
            if isinstance(r, Exception):
                logger.error("Subtask '%s' failed: %s", st.description, r)
                final.append(SubTaskResult(
                    description=st.description,
                    content="",
                    error=str(r),
                ))
            else:
                final.append(r)
        return final
