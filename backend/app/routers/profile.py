"""GET /me — the player's profile, streak, and per-track XP (GDD §3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import AuthedUser, get_current_user
from ..models import MeResponse, StreakInfo
from ..service import get_or_create_user
from ..store import Store, get_store

router = APIRouter()


@router.get("/me", response_model=MeResponse)
def me(
    auth: AuthedUser = Depends(get_current_user),
    store: Store = Depends(get_store),
) -> MeResponse:
    user = get_or_create_user(store, auth)
    s = user["streak"]
    return MeResponse(
        uid=user["uid"],
        handle=user["handle"],
        display_name=user["display_name"],
        anonymous=user["anonymous"],
        created_at=user["created_at"],
        streak=StreakInfo(
            current=s["current"],
            longest=s["longest"],
            freezes_available=s["freezes_available"],
            last_played_date=s.get("last_played_date"),
        ),
        tracks=user["tracks"],
    )
