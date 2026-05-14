from pydantic import BaseModel, Field


class MeResponse(BaseModel):
    user_id: str
    display_name: str | None = None
    timezone: str | None = None


class MeUpdate(BaseModel):
    """Partial update — only fields explicitly sent are applied (via
    `model_dump(exclude_unset=True)` server-side)."""

    display_name: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=64)
