"""POST /submit — server-authoritative answer check (GDD §8.1-§8.3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import AuthedUser, get_current_user
from ..config import Settings, get_settings
from ..content import ContentIndex, get_content, grade
from ..models import SubmitRequest, SubmitResponse
from ..scoring import challenge_score
from ..seed import build_stack
from ..service import get_or_create_run, get_or_create_user, validate_date, validate_track
from ..store import Store, get_store
from ..time_source import now_ms

router = APIRouter()


@router.post("/submit", response_model=SubmitResponse)
def submit(
    body: SubmitRequest,
    auth: AuthedUser = Depends(get_current_user),
    store: Store = Depends(get_store),
    index: ContentIndex = Depends(get_content),
    settings: Settings = Depends(get_settings),
) -> SubmitResponse:
    validate_date(body.date)
    validate_track(body.track)

    challenge = index.get(body.challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="unknown challenge")

    user = get_or_create_user(store, auth)
    stack_id, ids = build_stack(index, body.date, body.track)
    if body.challenge_id not in ids:
        # Prevent grinding a challenge that isn't part of today's stack.
        raise HTTPException(status_code=400, detail="challenge not in today's stack")

    run = get_or_create_run(store, user["uid"], body.date, body.track, stack_id)
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
