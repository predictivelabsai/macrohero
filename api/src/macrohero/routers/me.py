from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from macrohero.auth.clerk import current_user_id
from macrohero.db.models import User
from macrohero.db.session import get_db
from macrohero.schemas.me import MeResponse, MeUpdate

router = APIRouter(tags=["me"])


async def _ensure_user(db: AsyncSession, user_id: str) -> User:
    """Lazy upsert: get-or-create a user row from the verified Clerk JWT."""
    user = await db.get(User, user_id)
    if user is not None:
        return user
    stmt = pg_insert(User).values(id=user_id).on_conflict_do_nothing(index_elements=["id"])
    await db.execute(stmt)
    await db.commit()
    user = await db.get(User, user_id)
    assert user is not None, "user upsert failed"
    return user


def _to_response(user: User) -> MeResponse:
    return MeResponse(user_id=user.id, display_name=user.display_name, timezone=user.timezone)


@router.get("/me", response_model=MeResponse)
async def me(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    user = await _ensure_user(db, user_id)
    return _to_response(user)


@router.patch("/me", response_model=MeResponse)
async def update_me(
    payload: MeUpdate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    user = await _ensure_user(db, user_id)
    # Only update fields the client explicitly sent. Allows partial updates from
    # separate settings cards (display-name card vs timezone card).
    data = payload.model_dump(exclude_unset=True)
    if "display_name" in data:
        # Empty string → store NULL (treat as "cleared")
        val = data["display_name"]
        user.display_name = val.strip() if isinstance(val, str) and val.strip() else None
    if data.get("timezone"):
        user.timezone = data["timezone"]
    await db.commit()
    await db.refresh(user)
    return _to_response(user)
