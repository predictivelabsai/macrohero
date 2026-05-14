from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatAction(BaseModel):
    type: str
    id: str
    title: str
    url: str


class ChatReasoningPart(BaseModel):
    kind: Literal["reasoning"]
    text: str


class ChatTextPart(BaseModel):
    kind: Literal["text"]
    text: str


class ChatToolPart(BaseModel):
    kind: Literal["tool"]
    tool_name: str
    # Stream-protocol state of the tool call when persisted; "output-available"
    # means the tool ran to completion, "output-error" that it raised.
    state: Literal["output-available", "output-error"] = "output-available"
    # The arguments the LLM passed to the tool — used by the FE to render the
    # pill's contextual hint (e.g. the search query). Outputs are NOT
    # persisted here: large projection payloads live on ScenarioProjectionPart,
    # and search results are transient context for the model.
    input: dict[str, Any] | None = None
    action_id: str | None = None


class ScenarioProjectionPart(BaseModel):
    kind: Literal["scenario_projection"]
    data: dict[str, Any]


ChatMessagePart = Annotated[
    ChatReasoningPart | ChatTextPart | ChatToolPart | ScenarioProjectionPart,
    Field(discriminator="kind"),
]


class ChatMessageSchema(BaseModel):
    id: UUID
    ordinal: int
    role: Literal["user", "assistant"]
    content: str
    reasoning: str = ""
    actions: list[ChatAction] = Field(default_factory=list)
    parts: list[ChatMessagePart] = Field(default_factory=list)
    created_at: datetime


class ChatSessionSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionSummary):
    messages: list[ChatMessageSchema] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
