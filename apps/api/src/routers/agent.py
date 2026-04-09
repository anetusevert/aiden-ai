"""Minimal agent utility endpoints for workflow UX."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.dependencies.auth import RequestContext, require_viewer
from src.services.agent.llm_router import chat_completion

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentMessageRequest(BaseModel):
    message: str
    context: dict[str, Any] | None = None


class AgentMessageResponse(BaseModel):
    summary: str


@router.post("/message", response_model=AgentMessageResponse)
async def send_agent_message(
    body: AgentMessageRequest,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
) -> AgentMessageResponse:
    context_blob = json.dumps(body.context or {}, ensure_ascii=False, indent=2)
    prompt = (
        "You are Amin, a GCC and KSA legal intelligence assistant.\n"
        "Respond in 2-3 concise sentences.\n\n"
        f"User message:\n{body.message}\n\n"
        f"Context:\n{context_blob}\n\n"
        f"User ID: {ctx.user.id}"
    )

    response = await chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are Amin. Keep the summary concise, polished, and useful.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )

    summary = (response.choices[0].message.content or "").strip()
    return AgentMessageResponse(summary=summary)
