"""GET /daily/{date}?track= — today's stack, WITHOUT answers (GDD §8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import AuthedUser, get_current_user
from ..content import ContentIndex, get_content
from ..models import ChallengePublic, DailyResponse
from ..seed import build_stack
from ..service import get_or_create_run, get_or_create_user, validate_date, validate_track
from ..store import Store, get_store
from ..config import get_settings

router = APIRouter()


@router.get("/daily/{date}", response_model=DailyResponse)
def get_daily(
    date: str,
    track: str = Query(...),
    auth: AuthedUser = Depends(get_current_user),
    store: Store = Depends(get_store),
    index: ContentIndex = Depends(get_content),
) -> DailyResponse:
    validate_date(date)
    validate_track(track)

    user = get_or_create_user(store, auth)
    stack_id, ids = build_stack(index, date, track)
    if not ids:
        raise HTTPException(status_code=404, detail="no stack available for this track")

    run = get_or_create_run(store, user["uid"], date, track, stack_id)

    challenges = []
    for cid in ids:
        challenge = index.get(cid)
        if challenge is None:
            continue
        pub: ChallengePublic = challenge.public_payload()
        progress = run["answers"].get(cid)
        if progress:
            pub.attempts_used = progress["attempts"]
            pub.resolved = progress["resolved"]
            pub.correct = progress["correct"]
            if progress["resolved"]:
                pub.explanation = challenge.explanation  # safe to reveal once resolved
        challenges.append(pub)

    return DailyResponse(
        date=date,
        track=track,
        stack_id=stack_id,
        attempts_per_challenge=get_settings().attempts_per_challenge,
        started_at=run["started_at"],
        completed=run["completed"],
        challenges=challenges,
    )
