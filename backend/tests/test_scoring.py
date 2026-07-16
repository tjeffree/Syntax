"""Scoring, XP/levels, and streak logic (pure functions)."""
from __future__ import annotations

from app.scoring import (
    challenge_score,
    is_implausible,
    level_for_xp,
    update_streak,
    xp_for_score,
)


def test_first_try_beats_second_try():
    fast_first = challenge_score("big-o", correct=True, attempts=1, elapsed_ms=5000)
    fast_second = challenge_score("big-o", correct=True, attempts=2, elapsed_ms=5000)
    assert fast_first > fast_second


def test_speed_bonus_decays():
    quick = challenge_score("bug-spot", True, 1, 1000)
    slow = challenge_score("bug-spot", True, 1, 29000)
    assert quick > slow
    # Past par earns no bonus, only base.
    over_par = challenge_score("bug-spot", True, 1, 60000)
    assert over_par == 1000


def test_fail_scores_zero():
    assert challenge_score("parsons", correct=False, attempts=2, elapsed_ms=1000) == 0


def test_levels_increase_with_xp():
    assert level_for_xp(0) == 1
    assert level_for_xp(100) == 2
    assert level_for_xp(400) == 3
    assert level_for_xp(50) < level_for_xp(500)


def test_xp_from_score():
    assert xp_for_score(1350) == 135


def test_implausible_only_when_too_fast():
    assert is_implausible("parsons", correct=True, elapsed_ms=100) is True
    assert is_implausible("parsons", correct=True, elapsed_ms=30000) is False
    assert is_implausible("parsons", correct=False, elapsed_ms=100) is False


def test_streak_first_play():
    s, freeze = update_streak(
        {"current": 0, "longest": 0, "freezes_available": 1, "last_played_date": None},
        "2026-07-16",
    )
    assert s["current"] == 1 and s["longest"] == 1 and freeze is False


def test_streak_consecutive_day():
    base = {"current": 3, "longest": 3, "freezes_available": 1, "last_played_date": "2026-07-15"}
    s, _ = update_streak(base, "2026-07-16")
    assert s["current"] == 4 and s["longest"] == 4


def test_streak_same_day_idempotent():
    base = {"current": 4, "longest": 4, "freezes_available": 1, "last_played_date": "2026-07-16"}
    s, _ = update_streak(base, "2026-07-16")
    assert s["current"] == 4


def test_streak_freeze_bridges_one_missed_day():
    base = {"current": 5, "longest": 5, "freezes_available": 1, "last_played_date": "2026-07-14"}
    s, freeze = update_streak(base, "2026-07-16")  # missed the 15th
    assert freeze is True
    assert s["current"] == 6
    assert s["freezes_available"] == 0


def test_streak_resets_after_long_gap():
    base = {"current": 9, "longest": 9, "freezes_available": 0, "last_played_date": "2026-07-01"}
    s, _ = update_streak(base, "2026-07-16")
    assert s["current"] == 1
    assert s["longest"] == 9  # longest preserved
