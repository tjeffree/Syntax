"""Date-specific challenge stacks backed by seed files or Firestore."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from .config import Settings, get_settings
from .content import Challenge, get_content, validate_raw_challenge
from .firestore_client import get_firestore_client
from .seed import build_stack
from .time_source import now


@dataclass(frozen=True)
class DailyStack:
    stack_id: str
    challenge_ids: list[str]
    challenges: list[Challenge]


class DailyStackUnavailable(Exception):
    pass


class ChallengeRepository(Protocol):
    def get_stack(self, game_date: str, track: str) -> DailyStack: ...


class SeedChallengeRepository:
    def get_stack(self, game_date: str, track: str) -> DailyStack:
        index = get_content()
        stack_id, ids = build_stack(index, game_date, track)
        challenges = [index.get(cid) for cid in ids]
        return DailyStack(stack_id, ids, [c for c in challenges if c is not None])


class FirestoreChallengeRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._db = get_firestore_client(settings)

    def get_stack(self, game_date: str, track: str) -> DailyStack:
        snapshot = self._db.collection("dailyStacks").document(game_date).get()
        if not snapshot.exists:
            raise DailyStackUnavailable(f"no stack published for {game_date}")
        manifest = snapshot.to_dict() or {}
        if manifest.get("status") != "published":
            raise DailyStackUnavailable(f"stack for {game_date} is not published")
        ids = list((manifest.get("tracks") or {}).get(track) or [])
        if not ids:
            raise DailyStackUnavailable(f"no {track} stack published for {game_date}")

        challenges: list[Challenge] = []
        for challenge_id in ids:
            challenge_snapshot = self._db.collection("challenges").document(challenge_id).get()
            if not challenge_snapshot.exists:
                raise DailyStackUnavailable(f"published stack references missing challenge {challenge_id}")
            raw = challenge_snapshot.to_dict() or {}
            if raw.get("game_date") != game_date or raw.get("status") != "approved":
                raise DailyStackUnavailable(f"challenge {challenge_id} is not an approved member of {game_date}")
            gameplay_raw = {key: raw[key] for key in (
                "id", "type", "track", "difficulty", "skillNodes", "payload", "answer", "explanation"
            ) if key in raw}
            challenges.append(validate_raw_challenge(gameplay_raw, self._settings))
        return DailyStack(f"{game_date}:{track}", ids, challenges)


@lru_cache
def get_challenge_repository() -> ChallengeRepository:
    settings = get_settings()
    if settings.content_mode == "seed":
        return SeedChallengeRepository()
    if settings.content_mode == "firestore":
        return FirestoreChallengeRepository(settings)
    raise ValueError("CONTENT_MODE must be 'seed' or 'firestore'")


def unavailable_status(game_date: str) -> int:
    """Expired dates are gone; a missing current/future stack is operational."""
    return 404 if game_date < now().date().isoformat() else 503
