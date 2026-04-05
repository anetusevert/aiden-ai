"""The Amin agent — main orchestration loop.

Integrates tool calling, permission pipeline, multi-agent forking,
title auto-generation, and twin learning.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Conversation, Message
from src.models.twin import UserTwin
from src.services.agent.context_builder import (
    build_messages,
    build_screen_context,
    build_system_prompt,
)
from src.services.agent.llm_router import chat_completion, stream_chat_completion
from src.services.agent.soul_loader import load_soul_files
from src.services.agent.sub_agent import SubAgentRunner
from src.services.agent.title_generator import generate_title
from src.services.agent.token_counter import count_tokens
from src.services.agent.tool_executor import execute_tool_calls
from src.services.agent.tool_registry import ToolRegistry
from src.services.agent.tools import register_all_tools
from src.services.agent.twin_manager import TwinManager

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


class AminAgent:
    """The Amin agent — orchestrates LLM calls, tool execution, and twin learning."""

    def __init__(
        self,
        db: AsyncSession,
        user_id: str,
        workspace_id: str,
        tenant_id: str,
        confirmation_queue: asyncio.Queue | None = None,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.tenant_id = tenant_id
        self.confirmation_queue = confirmation_queue

        self._registry = ToolRegistry()
        register_all_tools(self._registry)

        self._tool_context = {
            "db": db,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "tenant_id": tenant_id,
        }

    async def process_message(
        self,
        conversation_id: str,
        user_message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Process a user message and yield streaming response events.

        Yields dicts with these event types:
        - {"type": "status", "content": "..."}
        - {"type": "tool_start", "tool": "...", "params": {...}}
        - {"type": "tool_result", "tool": "...", "summary": "..."}
        - {"type": "confirmation_required", "tool": "...", "params": {...}, "risk_level": "..."}
        - {"type": "subtask_start", "tasks": [...]}
        - {"type": "subtask_complete", "task": "...", "summary": "..."}
        - {"type": "token", "content": "..."}
        - {"type": "title_update", "title": "..."}
        - {"type": "message_complete", "message_id": "..."}
        - {"type": "error", "content": "..."}
        """
        try:
            # 1. Save user message
            user_msg = Message(
                conversation_id=conversation_id,
                role="user",
                content=user_message,
                token_count=count_tokens(user_message),
            )
            self.db.add(user_msg)
            await self.db.flush()

            # 2. Load soul + twin
            soul = load_soul_files()
            twin = await TwinManager.get_or_create_twin(self.db, self.user_id)
            screen_context_text = await build_screen_context(self.user_id)

            # 3. Build system prompt
            system_prompt = build_system_prompt(soul, twin, screen_context_text)

            # 4. Load conversation history
            result = await self.db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            history = list(result.scalars().all())
            llm_messages = build_messages(history, system_prompt)

            # 4b. Check for multi-agent opportunity
            parallel_result = await self._try_parallel_execution(
                user_message, system_prompt, llm_messages
            )
            if parallel_result is not None:
                final_content = parallel_result["content"]
                async for event in parallel_result["events"]:
                    yield event
            else:
                # 5. Standard agent loop with tool calls
                final_content = ""
                async for event in self._run_agent_loop(
                    conversation_id, llm_messages
                ):
                    if event.get("_final_content") is not None:
                        final_content = event["_final_content"]
                    else:
                        yield event

            # 8. Save assistant message
            assistant_final = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=final_content,
                token_count=count_tokens(final_content),
            )
            self.db.add(assistant_final)
            await self.db.flush()

            # 9. Record twin observations
            try:
                observations = TwinManager.extract_observations_from_interaction(
                    user_message=user_message,
                    assistant_message=final_content,
                )
                for obs in observations:
                    await TwinManager.record_observation(
                        self.db, self.user_id, obs["type"], obs["data"],
                    )
            except Exception as e:
                logger.warning("Failed to record twin observations: %s", e)

            await self.db.commit()

            # 10. Yield message_complete
            yield {"type": "message_complete", "message_id": assistant_final.id}

            # 11. Title auto-generation (non-blocking, after commit)
            async for event in self._maybe_generate_title(conversation_id, user_message, final_content):
                yield event

        except Exception as e:
            logger.error("Agent error: %s", e, exc_info=True)
            await self.db.rollback()
            yield {"type": "error", "content": str(e)}

    async def _run_agent_loop(
        self,
        conversation_id: str,
        llm_messages: list[dict[str, Any]],
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the standard tool-calling agent loop.

        Yields events and a final _final_content sentinel.
        """
        openai_tools = self._registry.get_openai_tools()
        final_content = ""

        for round_num in range(MAX_TOOL_ROUNDS + 1):
            force_no_tools = round_num >= MAX_TOOL_ROUNDS
            tools_for_call = None if force_no_tools else (openai_tools or None)

            yield {
                "type": "status",
                "content": "Thinking..." if round_num == 0 else "Processing tool results...",
            }

            if not force_no_tools and tools_for_call:
                response = await chat_completion(
                    messages=llm_messages, tools=tools_for_call,
                )
                choice = response.choices[0]
                msg = choice.message

                if msg.tool_calls:
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
                    assistant_msg = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        tool_calls=tc_data,
                        model=getattr(response, "model", None),
                    )
                    self.db.add(assistant_msg)
                    await self.db.flush()

                    for tc in msg.tool_calls:
                        try:
                            params = json.loads(tc.function.arguments)
                        except (json.JSONDecodeError, TypeError):
                            params = {}
                        yield {
                            "type": "tool_start",
                            "tool": tc.function.name,
                            "params": params,
                        }

                    # Permission pipeline: check if any tool requires confirmation
                    confirmed_calls = []
                    for tc in msg.tool_calls:
                        tool_def = self._registry.get_by_name(tc.function.name)
                        if tool_def and tool_def.requires_confirmation:
                            try:
                                params = json.loads(tc.function.arguments)
                            except (json.JSONDecodeError, TypeError):
                                params = {}

                            yield {
                                "type": "confirmation_required",
                                "tool": tc.function.name,
                                "params": params,
                                "risk_level": tool_def.risk_level,
                            }

                            approved = await self._wait_for_confirmation(tc.function.name)
                            if not approved:
                                tool_msg = Message(
                                    conversation_id=conversation_id,
                                    role="tool",
                                    content=f"Tool '{tc.function.name}' was denied by the user.",
                                    tool_call_id=tc.id,
                                )
                                self.db.add(tool_msg)
                                llm_messages.append({
                                    "role": "assistant",
                                    "tool_calls": [tc_data[msg.tool_calls.index(tc)]],
                                })
                                llm_messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "content": f"Tool '{tc.function.name}' was denied by the user.",
                                })
                                yield {
                                    "type": "tool_result",
                                    "tool": tc.function.name,
                                    "summary": "Denied by user",
                                }
                                continue
                        confirmed_calls.append(tc)

                    if confirmed_calls:
                        tool_results = await execute_tool_calls(
                            confirmed_calls, self._registry, self._tool_context,
                        )

                        for tc, tr in zip(confirmed_calls, tool_results):
                            summary = tr.content[:200] if tr.content else (tr.error or "Done")
                            yield {
                                "type": "tool_result",
                                "tool": tc.function.name,
                                "summary": summary,
                            }

                            tool_msg = Message(
                                conversation_id=conversation_id,
                                role="tool",
                                content=tr.error or tr.content,
                                tool_call_id=tc.id,
                            )
                            self.db.add(tool_msg)

                        await self.db.flush()

                        llm_messages.append({
                            "role": "assistant",
                            "tool_calls": tc_data,
                        })
                        for tc, tr in zip(confirmed_calls, tool_results):
                            llm_messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tr.error or tr.content,
                            })

                    continue

                if msg.content:
                    final_content = msg.content
                    for token in _chunk_text(final_content, 8):
                        yield {"type": "token", "content": token}
                    break

            # Streaming final response
            yield {"type": "status", "content": "Composing response..."}
            final_content = ""
            async for chunk in stream_chat_completion(
                messages=llm_messages, tools=None,
            ):
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        final_content += delta.content
                        yield {"type": "token", "content": delta.content}
            break

        yield {"_final_content": final_content}

    async def _try_parallel_execution(
        self,
        user_message: str,
        system_prompt: str,
        llm_messages: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Detect and execute parallel sub-tasks if applicable.

        Returns {"content": str, "events": AsyncIterator} or None.
        """
        subtasks = await SubAgentRunner.detect_subtasks(
            user_message, self._registry.get_all()
        )
        if not subtasks:
            return None

        async def _events() -> AsyncIterator[dict[str, Any]]:
            yield {
                "type": "status",
                "content": f"I'll work on {len(subtasks)} tasks in parallel...",
            }
            yield {
                "type": "subtask_start",
                "tasks": [st.description for st in subtasks],
            }

            results = await SubAgentRunner.run_parallel(
                subtasks, system_prompt, self._registry, self._tool_context,
            )

            for r in results:
                yield {
                    "type": "subtask_complete",
                    "task": r.description,
                    "summary": (r.content[:300] if r.content else r.error or "Completed"),
                }

            # Synthesize final response from all sub-results
            synthesis_prompt = (
                "You are Amin, an AI legal colleague. The following sub-tasks were completed in parallel. "
                "Synthesize their results into a single coherent response for the lawyer.\n\n"
            )
            for r in results:
                synthesis_prompt += f"### {r.description}\n{r.content}\n\n"

            yield {"type": "status", "content": "Synthesizing results..."}

            synthesis_content = ""
            async for chunk in stream_chat_completion(
                messages=[
                    {"role": "system", "content": synthesis_prompt},
                    {"role": "user", "content": "Combine these results into one response."},
                ],
                tools=None,
            ):
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        synthesis_content += delta.content
                        yield {"type": "token", "content": delta.content}

            nonlocal captured_content
            captured_content = synthesis_content

        captured_content = ""
        event_gen = _events()

        # We need to consume events while also capturing the final content
        # Use a wrapper that stores events
        events_buffer: list[dict[str, Any]] = []

        async for evt in event_gen:
            events_buffer.append(evt)

        async def _replay() -> AsyncIterator[dict[str, Any]]:
            for evt in events_buffer:
                yield evt

        return {"content": captured_content, "events": _replay()}

    async def _wait_for_confirmation(self, tool_name: str) -> bool:
        """Wait for user confirmation of a tool execution.

        Returns True if approved, False if denied or timeout.
        """
        if self.confirmation_queue is None:
            return True  # No queue = auto-approve (e.g. REST endpoint)

        try:
            result = await asyncio.wait_for(
                self.confirmation_queue.get(),
                timeout=120.0,
            )
            if isinstance(result, dict):
                return result.get("approved", False) and result.get("tool") == tool_name
            return False
        except asyncio.TimeoutError:
            logger.warning("Confirmation timeout for tool %s", tool_name)
            return False

    async def _maybe_generate_title(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Generate and update conversation title if this is the first exchange."""
        try:
            conv = await self.db.get(Conversation, conversation_id)
            if conv is None or conv.title:
                return

            msg_count = await self.db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.role == "user",
                )
            )
            user_msgs = list(msg_count.scalars().all())
            if len(user_msgs) > 1:
                return

            title = await generate_title(user_message, assistant_message)
            conv.title = title
            await self.db.commit()

            yield {"type": "title_update", "title": title}

        except Exception as e:
            logger.warning("Title generation failed: %s", e)


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into chunks for simulated streaming."""
    words = text.split(" ")
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= chunk_size:
            chunks.append(" ".join(current) + " ")
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks
