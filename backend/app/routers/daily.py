"""GET /daily/{date}?track= — today's stack, WITHOUT answers (GDD §8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import AuthedUser, get_current_user
from ..content_repository import DailyStackUnavailable, ChallengeRepository, get_challenge_repository, unavailable_status
from ..models import ChallengePublic, DailyResponse
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
    repository: ChallengeRepository = Depends(get_challenge_repository),
) -> DailyResponse:
    validate_date(date)
    validate_track(track)

    user = get_or_create_user(store, auth)
    try:
        stack = repository.get_stack(date, track)
    except DailyStackUnavailable as exc:
        raise HTTPException(status_code=unavailable_status(date), detail=str(exc)) from exc

    run = get_or_create_run(store, user["uid"], date, track, stack.stack_id)

    challenges = []
    for challenge in stack.challenges:
        cid = challenge.id
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
        stack_id=stack.stack_id,
        attempts_per_challenge=get_settings().attempts_per_challenge,
        started_at=run["started_at"],
        completed=run["completed"],
        challenges=challenges,
    )
