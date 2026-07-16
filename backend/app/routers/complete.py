"""POST /complete — finalize the day's run: XP, streak, leaderboard (GDD §6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import AuthedUser, get_current_user
from ..content import ContentIndex, get_content
from ..models import (
    ChallengeResult,
    CompleteRequest,
    CompleteResponse,
    StreakInfo,
    TrackXp,
)
from ..scoring import is_implausible, level_for_xp, update_streak, xp_for_score
from ..seed import build_stack
from ..service import get_or_create_user, rank_entries, validate_date, validate_track
from ..store import Store, get_store
from ..time_source import iso, now

router = APIRouter()


@router.post("/complete", response_model=CompleteResponse)
def complete(
    body: CompleteRequest,
    auth: AuthedUser = Depends(get_current_user),
    store: Store = Depends(get_store),
    index: ContentIndex = Depends(get_content),
) -> CompleteResponse:
    validate_date(body.date)
    validate_track(body.track)

    user = get_or_create_user(store, auth)
    _, ids = build_stack(index, body.date, body.track)
    run = store.get_run(user["uid"], body.date, body.track)
    if run is None:
        raise HTTPException(status_code=400, detail="no run to complete; fetch /daily first")

    # Idempotency: one finalized run per player per day (GDD §8.4).
    if run.get("completed"):
        return CompleteResponse(**run["completion"])

    missing = [cid for cid in ids if not run["answers"].get(cid, {}).get("resolved")]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"error": "stack not complete", "unresolved": missing},
        )

    results = []
    total_score = 0
    total_ms = 0
    quarantined = False
    for cid in ids:
        a = run["answers"][cid]
        total_score += a["score"]
        total_ms += a["elapsed_ms"]
        if is_implausible(a.get("type", ""), a["correct"], a["elapsed_ms"]):
            quarantined = True
        results.append(
            ChallengeResult(
                challenge_id=cid,
                type=a.get("type", index.get(cid).type if index.get(cid) else "bug-spot"),
                correct=a["correct"],
                attempts=a["attempts"],
                score=a["score"],
                elapsed_ms=a["elapsed_ms"],
            )
        )

    # XP allocation into the day's track (GDD §1 step 5).
    track_state = user["tracks"].setdefault(body.track, {"xp": 0, "level": 1})
    xp_before = int(track_state["xp"])
    xp_delta = xp_for_score(total_score)
    xp_after = xp_before + xp_delta
    level_before = level_for_xp(xp_before)
    level_after = level_for_xp(xp_after)
    track_state["xp"] = xp_after
    track_state["level"] = level_after

    # Streak update (GDD §1 enhancements).
    new_streak, freeze_used = update_streak(user["streak"], body.date)
    user["streak"] = new_streak
    store.save_user(user)

    leaderboard_rank = None
    if not quarantined:
        entry = {
            "uid": user["uid"],
            "handle": user["handle"],
            "score": total_score,
            "total_ms": total_ms,
            "track": body.track,
        }
        store.upsert_leaderboard_entry(body.date, body.track, entry)
        ranked = rank_entries(store.get_leaderboard(body.date, body.track), user["uid"])
        for row in ranked:
            if row["uid"] == user["uid"]:
                leaderboard_rank = row["rank"]
                break

    response = CompleteResponse(
        date=body.date,
        track=body.track,
        score=total_score,
        total_ms=total_ms,
        results=results,
        streak=StreakInfo(
            current=new_streak["current"],
            longest=new_streak["longest"],
            freezes_available=new_streak["freezes_available"],
            last_played_date=new_streak["last_played_date"],
            freeze_used=freeze_used,
        ),
        xp=TrackXp(
            track=body.track,
            xp_before=xp_before,
            xp_after=xp_after,
            xp_delta=xp_delta,
            level_before=level_before,
            level_after=level_after,
        ),
        quarantined=quarantined,
        leaderboard_rank=leaderboard_rank,
    )

    run["completed"] = True
    run["completed_at"] = iso(now())
    run["completion"] = response.model_dump()
    store.save_run(run)

    return response
