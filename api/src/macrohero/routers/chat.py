"""Chat endpoints — persisted sessions + streaming agent responses.

Wire shape:

- ``GET    /chat/sessions``                    list the user's sessions
- ``POST   /chat/sessions``                    create a new (empty) session
- ``GET    /chat/sessions/{id}``               session detail with all messages
- ``DELETE /chat/sessions/{id}``               delete a session
- ``POST   /chat/sessions/{id}/messages``      send a user message; the response
                                              streams Vercel AI SDK v5 data-stream
                                              SSE events for the assistant turn.

The streaming endpoint:
1. persists the user's turn (assigning the next ordinal),
2. runs the LangGraph agent against the full prior history,
3. relays AI SDK events to the client as they arrive, and
4. persists the resulting assistant turn (text + action list) at the end.
"""

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from macrohero.auth.clerk import current_user_id
from macrohero.chat.agent import stream_chat
from macrohero.db.models import ChatMessage, ChatSession, User
from macrohero.db.session import get_db
from macrohero.schemas.chat import (
    ChatAction,
    ChatMessageSchema,
    ChatSessionDetail,
    ChatSessionSummary,
    SendMessageRequest,
)

router = APIRouter(prefix="/chat", tags=["chat"])


async def _ensure_user(db: AsyncSession, user_id: str) -> None:
    user = await db.get(User, user_id)
    if user is not None:
        return
    stmt = pg_insert(User).values(id=user_id).on_conflict_do_nothing(index_elements=["id"])
    await db.execute(stmt)
    await db.commit()


async def _get_owned_session(db: AsyncSession, user_id: str, session_id: UUID) -> ChatSession:
    s = await db.get(ChatSession, session_id)
    if s is None or s.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return s


def _to_session_summary(s: ChatSession) -> ChatSessionSummary:
    return ChatSessionSummary(
        id=s.id, title=s.title, created_at=s.created_at, updated_at=s.updated_at
    )


def _to_message_schema(m: ChatMessage) -> ChatMessageSchema:
    return ChatMessageSchema(
        id=m.id,
        ordinal=m.ordinal,
        role=m.role,  # type: ignore[arg-type]
        content=m.content,
        reasoning=m.reasoning or "",
        actions=[ChatAction(**a) for a in (m.actions_jsonb or [])],
        parts=list(m.parts_jsonb or []),  # type: ignore[arg-type]
        created_at=m.created_at,
    )


@router.get("/sessions", response_model=list[ChatSessionSummary])
async def list_sessions(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ChatSessionSummary]:
    await _ensure_user(db, user_id)
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
        .limit(100)
    )
    result = await db.execute(stmt)
    return [_to_session_summary(s) for s in result.scalars().all()]


@router.post("/sessions", response_model=ChatSessionDetail, status_code=status.HTTP_201_CREATED)
async def create_session(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionDetail:
    await _ensure_user(db, user_id)
    session = ChatSession(user_id=user_id, title="New chat")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionDetail(**_to_session_summary(session).model_dump(), messages=[])


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: UUID,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionDetail:
    session = await _get_owned_session(db, user_id, session_id)
    msg_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(asc(ChatMessage.ordinal))
    )
    msg_result = await db.execute(msg_stmt)
    return ChatSessionDetail(
        **_to_session_summary(session).model_dump(),
        messages=[_to_message_schema(m) for m in msg_result.scalars().all()],
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    session = await _get_owned_session(db, user_id, session_id)
    await db.delete(session)
    await db.commit()


def _truncate_title(content: str, limit: int = 60) -> str:
    cleaned = " ".join(content.split())
    if len(cleaned) <= limit:
        return cleaned or "New chat"
    return cleaned[: limit - 1].rstrip() + "…"


def _format_sse(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


def _stream_response(stream: AsyncIterator[bytes]) -> StreamingResponse:
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


async def _stream_and_persist_assistant_turn(
    *,
    user_id: str,
    db: AsyncSession,
    session: ChatSession,
    assistant_ordinal: int,
    history: list[dict[str, str]],
    prelude: list[dict] | None = None,
) -> AsyncIterator[bytes]:
    """Run one ReAct turn, relay AI SDK chunks as SSE, then persist the
    assistant message. ``prelude`` is a list of dicts to emit before the
    agent starts (used by /chat/start to surface the new session id)."""
    final_text = ""
    final_reasoning = ""
    final_actions: list[dict] = []
    final_parts: list[dict] = []

    if prelude:
        for evt in prelude:
            yield _format_sse(evt)

    try:
        async for evt in stream_chat(user_id=user_id, db=db, messages=history):
            if evt.get("type") == "_final":
                final_text = evt.get("text", "")
                final_reasoning = evt.get("reasoning", "")
                final_actions = evt.get("actions", [])
                final_parts = evt.get("parts", [])
                continue
            yield _format_sse(evt)
    except Exception as exc:
        yield _format_sse({"type": "error", "errorText": f"Chat agent error: {exc}"})
        yield b"data: [DONE]\n\n"
        return

    assistant_msg = ChatMessage(
        session_id=session.id,
        ordinal=assistant_ordinal,
        role="assistant",
        content=final_text,
        reasoning=final_reasoning,
        actions_jsonb=final_actions,
        parts_jsonb=final_parts,
    )
    db.add(assistant_msg)
    # Touch the session so onupdate bumps updated_at — keeps sidebar sorted.
    session.title = session.title
    await db.commit()

    yield b"data: [DONE]\n\n"


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    payload: SendMessageRequest,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    session = await _get_owned_session(db, user_id, session_id)

    # Append the user's message and load the full history we'll send to the
    # agent (DB-derived, so reload + idempotency are trivial).
    next_ordinal_stmt = select(func.coalesce(func.max(ChatMessage.ordinal), -1) + 1).where(
        ChatMessage.session_id == session_id
    )
    next_ordinal = (await db.execute(next_ordinal_stmt)).scalar_one()

    user_msg = ChatMessage(
        session_id=session_id,
        ordinal=next_ordinal,
        role="user",
        content=payload.content,
        actions_jsonb=[],
    )
    db.add(user_msg)

    # First user message becomes the session title.
    is_first_user_message = next_ordinal == 0
    if is_first_user_message:
        session.title = _truncate_title(payload.content)

    await db.commit()

    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(asc(ChatMessage.ordinal))
    )
    history_rows = (await db.execute(history_stmt)).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    return _stream_response(
        _stream_and_persist_assistant_turn(
            user_id=user_id,
            db=db,
            session=session,
            assistant_ordinal=next_ordinal + 1,
            history=history,
        )
    )


@router.post("/start")
async def start_session(
    payload: SendMessageRequest,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Create a session lazily, persist the first user message, and stream
    the assistant's reply. The new session id is announced to the client as
    a transient ``data-session`` chunk at the very start of the stream so
    the UI can switch the URL to ``/chat/{id}`` afterwards."""
    await _ensure_user(db, user_id)

    title = _truncate_title(payload.content)
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    await db.flush()  # populate session.id without committing yet

    user_msg = ChatMessage(
        session_id=session.id,
        ordinal=0,
        role="user",
        content=payload.content,
        actions_jsonb=[],
    )
    db.add(user_msg)
    await db.commit()

    history = [{"role": "user", "content": payload.content}]
    prelude = [
        {
            "type": "data-session",
            "id": f"sess_{session.id}",
            "data": {"sessionId": str(session.id), "title": title},
            "transient": True,
        }
    ]

    return _stream_response(
        _stream_and_persist_assistant_turn(
            user_id=user_id,
            db=db,
            session=session,
            assistant_ordinal=1,
            history=history,
            prelude=prelude,
        )
    )
