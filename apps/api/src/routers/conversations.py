"""Conversation routes for Amin agent chat sessions.

Endpoints for creating, listing, and interacting with conversations.
All endpoints require JWT auth and workspace context.
"""

import asyncio
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, get_workspace_context
from src.models.conversation import Conversation, Message
from src.services.agent.amin import AminAgent
from src.services.agent.realtime import register_connection, unregister_connection
from src.services.agent.screen_context import store_screen_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ---------- Schemas ----------

class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str | None
    status: str
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str | None
    tool_calls: Any | None = None
    created_at: str


class ConversationDetailResponse(BaseModel):
    id: str
    title: str | None
    status: str
    messages: list[MessageResponse]
    created_at: str
    updated_at: str


class MessageCreate(BaseModel):
    content: str


class MessageSendResponse(BaseModel):
    message: MessageResponse


class StatusResponse(BaseModel):
    status: str


# ---------- Endpoints ----------


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new conversation."""
    conv = Conversation(
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        title=body.title,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        status=conv.status,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conv_status: str = Query(default="active", alias="status"),
):
    """List conversations for the current user in the current workspace."""
    base_q = select(Conversation).where(
        Conversation.workspace_id == ctx.workspace.id,
        Conversation.user_id == ctx.user.id,
        Conversation.status == conv_status,
    )

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    items_q = base_q.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
    result = await db.execute(items_q)
    convs = result.scalars().all()

    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c.id,
                title=c.title,
                status=c.status,
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat(),
            )
            for c in convs
        ],
        total=total,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a conversation with all its messages."""
    conv = await _get_owned_conversation(db, conversation_id, ctx)

    messages_q = (
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    msgs = (await db.execute(messages_q)).scalars().all()

    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        status=conv.status,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                tool_calls=m.tool_calls,
                created_at=m.created_at.isoformat(),
            )
            for m in msgs
        ],
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.post("/{conversation_id}/messages", response_model=MessageSendResponse)
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Send a message to a conversation and get Amin's response (non-streaming)."""
    conv = await _get_owned_conversation(db, conversation_id, ctx)

    agent = AminAgent(
        db=db,
        user_id=ctx.user.id,
        workspace_id=ctx.workspace.id,
        tenant_id=ctx.tenant.id,
    )

    final_message: dict[str, Any] | None = None

    async for event in agent.process_message(conv.id, body.content):
        if event["type"] == "message_complete":
            final_msg_q = select(Message).where(Message.id == event["message_id"])
            result = await db.execute(final_msg_q)
            msg = result.scalar_one_or_none()
            if msg:
                final_message = {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
        elif event["type"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=event.get("content", "Agent error"),
            )

    if final_message is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No response generated",
        )

    return MessageSendResponse(
        message=MessageResponse(**final_message)
    )


@router.delete("/{conversation_id}", response_model=StatusResponse)
async def archive_conversation(
    conversation_id: str,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Archive a conversation (soft delete)."""
    conv = await _get_owned_conversation(db, conversation_id, ctx)

    await db.execute(
        update(Conversation)
        .where(Conversation.id == conv.id)
        .values(status="archived")
    )
    await db.commit()

    return StatusResponse(status="archived")


# ---------- Helpers ----------


async def _get_owned_conversation(
    db: AsyncSession,
    conversation_id: str,
    ctx: RequestContext,
) -> Conversation:
    """Load a conversation, verifying ownership."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == ctx.workspace.id,
            Conversation.user_id == ctx.user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv


# ---------- WebSocket ----------


async def conversation_ws(
    websocket: WebSocket,
    conversation_id: str,
):
    """WebSocket endpoint for streaming Amin responses.

    Auth: validates JWT from cookie or query param `token`.
    Supports message types: 'message' (chat), 'system_trigger' (silent UI trigger),
    'confirm_tool' (permission approval).
    """
    from src.database import async_session_maker
    from src.services.agent.heartbeat import HeartbeatService
    from src.utils.jwt import decode_access_token

    await websocket.accept()

    # Authenticate
    token: str | None = None
    cookies = websocket.cookies
    if "access_token" in cookies:
        token = cookies["access_token"]
    else:
        token = websocket.query_params.get("token")

    if not token:
        await websocket.send_json({"type": "error", "content": "Authentication required"})
        await websocket.close(code=4001)
        return

    try:
        payload = decode_access_token(token)
    except Exception:
        await websocket.send_json({"type": "error", "content": "Invalid token"})
        await websocket.close(code=4001)
        return

    user_id = payload.sub
    workspace_id = payload.workspace_id
    tenant_id = payload.tenant_id

    # Shared queue for tool confirmation messages
    confirmation_queue: asyncio.Queue = asyncio.Queue()

    await websocket.send_json({
        "type": "connected",
        "conversation_id": conversation_id,
    })
    await register_connection(user_id, websocket)

    # Check for heartbeat on connect
    try:
        async with async_session_maker() as db:
            heartbeat_event = await HeartbeatService.check_and_generate(
                db, user_id, workspace_id,
            )
            if heartbeat_event:
                await db.commit()
                await websocket.send_json(heartbeat_event)
    except Exception as e:
        logger.warning("Heartbeat check failed: %s", e)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            # Handle tool confirmation messages
            if msg_type == "confirm_tool":
                await confirmation_queue.put({
                    "tool": data.get("tool", ""),
                    "approved": data.get("approved", False),
                })
                continue

            if msg_type == "screen_context":
                await store_screen_context(
                    user_id,
                    {
                        "route": data.get("route"),
                        "page_title": data.get("page_title"),
                        "document": data.get("document"),
                        "ui_state": data.get("ui_state") or {},
                    },
                )
                continue

            if msg_type not in {"message", "system_trigger"} or not data.get("content"):
                await websocket.send_json(
                    {
                        "type": "error",
                        "content": "Expected {type: 'message'|'system_trigger', content: '...'}",
                    }
                )
                continue

            content = data["content"]
            is_system_trigger = msg_type == "system_trigger"
            is_greeting = content == "__greeting__"

            async with async_session_maker() as db:
                agent = AminAgent(
                    db=db,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    tenant_id=tenant_id,
                    confirmation_queue=confirmation_queue,
                    user_role=payload.role if hasattr(payload, 'role') else "VIEWER",
                )

                if is_greeting:
                    content = (
                        "[SYSTEM: The user just activated you. Greet them warmly and concisely. "
                        "Mention what you can help with based on the current context. "
                        "Keep it to 1-2 sentences. Do NOT echo this instruction.]"
                    )
                elif is_system_trigger:
                    content = (
                        "[SYSTEM: This is an internal product trigger, not a user-visible chat turn. "
                        "Do not produce a conversational reply unless the instruction explicitly requires it. "
                        "Prefer tool calls and UI events only. If a context pane update is appropriate, "
                        "use show_context_pane and stop. Do NOT echo this instruction.]\n\n"
                        + content
                    )

                async for event in agent.process_message(conversation_id, content):
                    if is_system_trigger and event.get("type") in {
                        "status",
                        "tool_start",
                        "tool_result",
                        "confirmation_required",
                        "subtask_start",
                        "subtask_complete",
                        "token",
                        "title_update",
                        "message_complete",
                    }:
                        continue
                    await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: conversation=%s user=%s", conversation_id, user_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
    finally:
        await unregister_connection(user_id, websocket)
