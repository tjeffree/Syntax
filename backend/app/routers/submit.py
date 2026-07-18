"""POST /submit — server-authoritative answer check (GDD §8.1-§8.3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import AuthedUser, get_current_user
from ..config import Settings, get_settings
from ..content import grade
from ..content_repository import DailyStackUnavailable, ChallengeRepository, get_challenge_repository, unavailable_status
from ..models import SubmitRequest, SubmitResponse
from ..scoring import challenge_score
from ..service import get_or_create_run, get_or_create_user, validate_date, validate_track
from ..store import Store, get_store
from ..time_source import now_ms

router = APIRouter()


@router.post("/submit", response_model=SubmitResponse)
def submit(
    body: SubmitRequest,
    auth: AuthedUser = Depends(get_current_user),
    store: Store = Depends(get_store),
    repository: ChallengeRepository = Depends(get_challenge_repository),
    settings: Settings = Depends(get_settings),
) -> SubmitResponse:
    validate_date(body.date)
    validate_track(body.track)

    try:
        stack = repository.get_stack(body.date, body.track)
    except DailyStackUnavailable as exc:
        raise HTTPException(status_code=unavailable_status(body.date), detail=str(exc)) from exc
    challenge = next((c for c in stack.challenges if c.id == body.challenge_id), None)
    if challenge is None:
        raise HTTPException(status_code=400, detail="challenge not in this day's stack")

    user = get_or_create_user(store, auth)
    run = get_or_create_run(store, user["uid"], body.date, body.track, stack.stack_id)
    if run["completed"]:
        raise HTTPException(status_code=400, detail="run already completed")

    prev = run["answers"].get(
        body.challenge_id,
        {"attempts": 0, "correct": False, "resolved": False, "elapsed_ms": 0, "score": 0},
    )
    if prev["resolved"]:
        raise HTTPException(status_code=400, detail="challenge already resolved")

    attempts = prev["attempts"] + 1
    correct = grade(challenge, body.answer_payload)
    max_attempts = settings.attempts_per_challenge
    resolved = correct or attempts >= max_attempts

    entry = dict(prev)
    entry["attempts"] = attempts
    entry.setdefault("type", challenge.type)
    entry.setdefault("first_submit_ms", now_ms())

    score: int | None = None
    explanation: str | None = None
    if resolved:
        # Server-side per-challenge clock: time since the previous resolve
        # (or the run start for the first challenge). clientElapsedMs is ignored
        # for scoring — accepted only as a sanity signal (GDD §8.2).
        elapsed = max(0, now_ms() - run["last_activity_ms"])
        run["last_activity_ms"] = now_ms()
        score = challenge_score(challenge.type, correct, attempts, elapsed)
        entry.update(
            {
                "resolved": True,
                "correct": correct,
                "elapsed_ms": elapsed,
                "score": score,
                "client_elapsed_ms": body.client_elapsed_ms,
            }
        )
        explanation = challenge.explanation
    else:
        entry.update({"resolved": False, "correct": False})

    run["answers"][body.challenge_id] = entry
    store.save_run(run)

    return SubmitResponse(
        correct=correct,
        resolved=resolved,
        attempts_remaining=0 if resolved else max_attempts - attempts,
        score=score,
        explanation=explanation,
    )
