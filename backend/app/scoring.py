"""Scoring, XP/levels, streaks, and plausibility (GDD §1, §3, §8).

All pure functions so they're trivially unit-testable and identical whether the
store is memory or Firestore.
"""
from __future__ import annotations

import math
from datetime import date as date_cls
from typing import Dict, Tuple

# Base points by attempt outcome (GDD §1 anti-frustration).
BASE_FIRST_TRY = 1000
BASE_SECOND_TRY = 600
BASE_FAIL = 0

# Max speed bonus and a "par" solve time per type (ms). Faster than par earns a
# fraction of the bonus; slower earns none. The clock is server-side.
SPEED_BONUS_MAX = 500
PAR_MS: Dict[str, int] = {
    "bug-spot": 30_000,
    "parsons": 60_000,
    "big-o": 20_000,
}
# Below this, a solve is implausibly fast and the run is quarantined (GDD §8.5).
MIN_HUMAN_MS: Dict[str, int] = {
    "bug-spot": 700,
    "parsons": 1_200,
    "big-o": 500,
}


def base_points(correct: bool, attempts: int) -> int:
    if not correct:
        return BASE_FAIL
    return BASE_FIRST_TRY if attempts <= 1 else BASE_SECOND_TRY


def speed_bonus(challenge_type: str, correct: bool, elapsed_ms: int) -> int:
    if not correct:
        return 0
    par = PAR_MS.get(challenge_type, 30_000)
    frac = max(0.0, (par - elapsed_ms) / par)
    return round(SPEED_BONUS_MAX * frac)


def challenge_score(challenge_type: str, correct: bool, attempts: int, elapsed_ms: int) -> int:
    return base_points(correct, attempts) + speed_bonus(challenge_type, correct, elapsed_ms)


def is_implausible(challenge_type: str, correct: bool, elapsed_ms: int) -> bool:
    if not correct:
        return False
    return elapsed_ms < MIN_HUMAN_MS.get(challenge_type, 500)


# --- XP / levels ----------------------------------------------------------- #
def level_for_xp(xp: int) -> int:
    """Smooth curve: each level needs progressively more XP.

    level = 1 + floor(sqrt(xp / 100)). Level 2 at 100xp, 3 at 400, 4 at 900...
    """
    return 1 + int(math.isqrt(max(0, xp) // 100))


def xp_for_score(score: int) -> int:
    return round(score / 10)


# --- streaks (GDD §1 enhancements) ---------------------------------------- #
def update_streak(streak: Dict, play_date: str) -> Tuple[Dict, bool]:
    """Advance a streak for a completed run on `play_date` (YYYY-MM-DD).

    Returns (new_streak, freeze_used). A single missed day is bridged by a
    Streak Freeze if one is available; a larger gap resets to 1.
    Idempotent: replaying the same date leaves the streak unchanged.
    """
    current = int(streak.get("current", 0))
    longest = int(streak.get("longest", 0))
    freezes = int(streak.get("freezes_available", 0))
    last = streak.get("last_played_date")

    freeze_used = False
    today = date_cls.fromisoformat(play_date)

    if last == play_date:
        pass  # already counted today — idempotent
    elif last is None:
        current = 1
    else:
        gap = (today - date_cls.fromisoformat(last)).days
        if gap == 1:
            current += 1
        elif gap == 2 and freezes > 0:
            freezes -= 1
            current += 1
            freeze_used = True
        else:
            current = 1  # missed too long (or clock went backwards)

    longest = max(longest, current)
    return (
        {
            "current": current,
            "longest": longest,
            "freezes_available": freezes,
            "last_played_date": play_date,
        },
        freeze_used,
    )
