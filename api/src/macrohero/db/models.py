import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from macrohero.db.base import SCHEMA, Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Clerk user ID
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    # User-chosen display name (independent from Clerk's profile data).
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # IANA timezone name (e.g., "America/New_York"). Null until detected/set.
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ChatSession(Base):
    """One conversation thread owned by a user. The sidebar lists these
    newest-first; messages live in :class:`ChatMessage`."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, server_default="New chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )


class ChatMessage(Base):
    """One message in a chat session. ``ordinal`` is the 0-based index used
    for ordering; ``actions_jsonb`` remains available for future structured
    chat side effects."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # Concatenated reasoning blocks emitted by thinking-mode models on this
    # turn. Blank for user turns and for non-thinking models. Joined with
    # double-newlines if there were multiple blocks (e.g. one before the
    # tool call and one after).
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    actions_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    # Ordered structural parts emitted during the assistant turn. Each item
    # is one of:
    #   {"kind": "reasoning", "text": "..."}
    #   {"kind": "text",      "text": "..."}
    # Drives the chat UI on reload so the bubble order matches what the user
    # saw live. Empty for user messages.
    parts_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_chat_messages_session_ordinal"),
        {"schema": SCHEMA},
    )
