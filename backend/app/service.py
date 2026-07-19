"""Shared domain logic between routers: user bootstrap, run bootstrap, ranking.

Kept separate from the HTTP layer so it stays store-agnostic and easy to test.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from fastapi import HTTPException

from .auth import AuthedUser
from .config import Settings
from .handles import generate_handle
from .store.base import Store
from .time_source import iso, now, now_ms

TRACKS = ("python", "javascript")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date(date: str) -> None:
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD")


def validate_track(track: str) -> None:
    if track not in TRACKS:
        raise HTTPException(status_code=422, detail=f"track must be one of {TRACKS}")


def default_user(auth: AuthedUser) -> Dict:
    # A generated handle, never the IdP's real name (privacy — the handle is all
    # we ever show on the leaderboard or in the UI).
    handle = generate_handle(auth.uid)
    return {
        "uid": auth.uid,
        "handle": handle,
        "display_name": handle,
        "anonymous": auth.anonymous,
        "created_at": iso(now()),
        "streak": {
            "current": 0,
            "longest": 0,
            "freezes_available": 1,  # one earnable freeze to start (GDD §1)
            "last_played_date": None,
        },
        "tracks": {t: {"xp": 0, "level": 1} for t in TRACKS},
    }


def get_or_create_user(store: Store, auth: AuthedUser) -> Dict:
    user = store.get_user(auth.uid)
    if user is None:
        user = default_user(auth)
        store.save_user(user)
        return user
    changed = False
    # Enforce the generated handle (mirrored into display_name) on every load.
    # This also scrubs legacy docs created under the old scheme (``anon-…`` / a
    # real name) the next time the player is seen — no separate migration needed.
    handle = generate_handle(auth.uid)
    for key in ("handle", "display_name"):
        if user.get(key) != handle:
            user[key] = handle
            changed = True
    # Drop any real name persisted by an earlier version.
    if user.pop("photo_url", None) is not None:
        changed = True
    if not auth.anonymous and user.get("anonymous"):
        user["anonymous"] = False
        changed = True
    if changed:
        store.save_user(user)
    return user


def new_run(uid: str, date: str, track: str, stack_id: str) -> Dict:
    ts = now_ms()
    return {
        "uid": uid,
        "date": date,
        "track": track,
        "stack_id": stack_id,
        "started_at": iso(now()),
        "started_ms": ts,
        "last_activity_ms": ts,  # per-challenge clock advances from here
        "answers": {},  # challenge_id -> {attempts, correct, resolved, elapsed_ms, score, ...}
        "completed": False,
    }


def get_or_create_run(store: Store, uid: str, date: str, track: str, stack_id: str) -> Dict:
    run = store.get_run(uid, date, track)
    if run is None:
        run = new_run(uid, date, track, stack_id)
        store.save_run(run)
    return run


def rank_entries(entries: List[Dict], me_uid: Optional[str]) -> List[Dict]:
    """Sort by score desc, then total time asc; attach 1-based rank + is_me."""
    ordered = sorted(entries, key=lambda e: (-int(e["score"]), int(e["total_ms"])))
    ranked: List[Dict] = []
    for i, e in enumerate(ordered, start=1):
        row = dict(e)
        row["rank"] = i
        row["is_me"] = me_uid is not None and e["uid"] == me_uid
        ranked.append(row)
    return ranked
