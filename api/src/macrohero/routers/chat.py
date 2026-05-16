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

import asyncio
import json
import logging
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
from macrohero.chat.title import summarize_title
from macrohero.db.models import ChatMessage, ChatSession, User
from macrohero.db.session import get_db, make_session
from macrohero.schemas.chat import (
    ChatAction,
    ChatMessageSchema,
    ChatSessionDetail,
    ChatSessionSummary,
    SendMessageRequest,
)

logger = logging.getLogger(__name__)

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


# DB column is String(200). The LLM summarizer caps its own output to the
# same value; this helper caps the placeholder we write synchronously while
# waiting for the summarizer to come back.
_TITLE_HARD_CAP = 200


def _initial_title(content: str) -> str:
    """Cheap, synchronous placeholder title — the first chunk of the user's
    message, whitespace-collapsed, hard-cut to the column cap. Replaced by
    the LLM-generated title shortly after via the background task scheduled
    in `_spawn_title_summary`."""
    cleaned = " ".join(content.split())
    if not cleaned:
        return "New chat"
    return cleaned[:_TITLE_HARD_CAP].rstrip()


# Strong references to fire-and-forget title-summary tasks so the event loop's
# garbage collector doesn't cancel them mid-flight. The done callback discards
# the task once it finishes (successfully or not).
_TITLE_TASKS: set[asyncio.Task[str | None]] = set()


async def _refine_session_title(session_id: UUID, content: str) -> str | None:
    """Background task: call the LLM summarizer and overwrite the placeholder
    title. Opens its own DB session because the request's session is closed by
    the time the streaming response finishes. Returns the new title on success
    (so the streaming endpoint can relay it to the client) or ``None`` if no
    update happened — summarizer error, missing row, DB failure, etc."""
    title = await summarize_title(content)
    if title is None:
        return None
    try:
        async with make_session() as db:
            session = await db.get(ChatSession, session_id)
            if session is None:
                return None
            session.title = title
            await db.commit()
            return title
    except Exception:
        logger.exception("title refinement failed to persist for session %s", session_id)
        return None


def _spawn_title_summary(session_id: UUID, content: str) -> asyncio.Task[str | None]:
    task = asyncio.create_task(_refine_session_title(session_id, content))
    _TITLE_TASKS.add(task)
    task.add_done_callback(_TITLE_TASKS.discard)
    return task


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
    title_task: asyncio.Task[str | None] | None = None,
) -> AsyncIterator[bytes]:
    """Run one ReAct turn, relay AI SDK chunks as SSE, then persist the
    assistant message. ``prelude`` is a list of dicts to emit before the
    agent starts (used by /chat/start to surface the new session id).
    ``title_task``, if given, is the background LLM title summarizer the
    caller scheduled when this turn is the first user message.

    Agent events and the eventual title-update event are merged through a
    single asyncio.Queue so the sidebar refresh fires the moment the
    summarizer finishes — typically mid-stream, since the flash summarizer
    is much faster than the agent's full reply."""
    final_text = ""
    final_reasoning = ""
    final_actions: list[dict] = []
    final_parts: list[dict] = []
    agent_errored = False

    if prelude:
        for evt in prelude:
            yield _format_sse(evt)

    # `("evt", payload)` items get yielded to the client; `("done", source)`
    # items tell the consumer that one producer has finished. The consumer
    # loop exits when both expected producers have signalled done.
    queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

    async def _produce_agent() -> None:
        nonlocal final_text, final_reasoning, final_actions, final_parts, agent_errored
        try:
            async for evt in stream_chat(user_id=user_id, db=db, messages=history):
                if evt.get("type") == "_final":
                    final_text = evt.get("text", "")
                    final_reasoning = evt.get("reasoning", "")
                    final_actions = evt.get("actions", [])
                    final_parts = evt.get("parts", [])
                    continue
                await queue.put(("evt", evt))
        except Exception as exc:
            agent_errored = True
            await queue.put(("evt", {"type": "error", "errorText": f"Chat agent error: {exc}"}))
        finally:
            await queue.put(("done", "agent"))

    async def _produce_title_update() -> None:
        # Shield so a wait_for timeout doesn't cancel the still-useful
        # background task (it stays alive in _TITLE_TASKS and finishes,
        # writing to the DB on its own — we just give up surfacing the
        # event to this particular client).
        try:
            new_title = await asyncio.wait_for(asyncio.shield(title_task), timeout=20)  # type: ignore[arg-type]
        except (TimeoutError, Exception):
            new_title = None
        if new_title is not None:
            await queue.put(
                (
                    "evt",
                    {
                        "type": "data-session-update",
                        "id": f"sess_update_{session.id}",
                        "data": {"sessionId": str(session.id), "title": new_title},
                        "transient": True,
                    },
                )
            )
        await queue.put(("done", "title"))

    pending: set[str] = {"agent"}
    agent_pump = asyncio.create_task(_produce_agent())
    title_pump: asyncio.Task[None] | None = None
    if title_task is not None:
        pending.add("title")
        title_pump = asyncio.create_task(_produce_title_update())

    while pending:
        kind, payload = await queue.get()
        if kind == "done":
            pending.discard(payload)  # type: ignore[arg-type]
        else:
            yield _format_sse(payload)  # type: ignore[arg-type]

    # Surface any exceptions raised by the pumps so they aren't swallowed.
    await agent_pump
    if title_pump is not None:
        await title_pump

    if agent_errored:
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

    # First user message becomes the session title: write a fast placeholder
    # synchronously, then spawn a background LLM summarizer that will overwrite
    # it with a proper title once the response below has started streaming.
    is_first_user_message = next_ordinal == 0
    if is_first_user_message:
        session.title = _initial_title(payload.content)

    await db.commit()

    title_task = (
        _spawn_title_summary(session_id, payload.content) if is_first_user_message else None
    )

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
            title_task=title_task,
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

    title = _initial_title(payload.content)
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

    title_task = _spawn_title_summary(session.id, payload.content)

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
            title_task=title_task,
        )
    )
