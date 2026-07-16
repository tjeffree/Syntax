"""GET /leaderboard/{date}?scope=&track= — global daily board (GDD §4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..auth import AuthedUser, get_current_user
from ..models import LeaderboardEntry, LeaderboardResponse
from ..service import get_or_create_user, rank_entries, validate_date, validate_track
from ..store import Store, get_store

router = APIRouter()


@router.get("/leaderboard/{date}", response_model=LeaderboardResponse)
def leaderboard(
    date: str,
    track: str = Query("python"),
    scope: str = Query("global"),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthedUser = Depends(get_current_user),
    store: Store = Depends(get_store),
) -> LeaderboardResponse:
    validate_date(date)
    validate_track(track)
    # Friends leaderboard is Phase 2 (GDD §9); global is the launch board.

    user = get_or_create_user(store, auth)
    ranked = rank_entries(store.get_leaderboard(date, track), user["uid"])

    me = None
    for row in ranked:
        if row["is_me"]:
            me = LeaderboardEntry(**row)
            break

    entries = [LeaderboardEntry(**row) for row in ranked[:limit]]
    return LeaderboardResponse(date=date, scope="global", entries=entries, me=me)
