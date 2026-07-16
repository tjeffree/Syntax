"""Pydantic models for the API surface (GDD §6 API surface v1).

Naming: `*Public` payloads are what the client is allowed to see. Correct
answers and explanations for unresolved challenges never appear in these.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Track = Literal["python", "javascript"]
ChallengeType = Literal["bug-spot", "parsons", "big-o"]


# --------------------------------------------------------------------------- #
# Challenge (server-side view includes the answer; never serialised to client) #
# --------------------------------------------------------------------------- #
class Challenge(BaseModel):
    id: str
    type: ChallengeType
    track: Track
    difficulty: int = Field(ge=1, le=5)
    skill_nodes: List[str] = Field(default_factory=list, alias="skillNodes")
    payload: Dict[str, Any]
    answer: Dict[str, Any]
    explanation: str

    model_config = {"populate_by_name": True}

    def public_payload(self) -> "ChallengePublic":
        return ChallengePublic(
            id=self.id,
            type=self.type,
            track=self.track,
            difficulty=self.difficulty,
            payload=self.payload,
        )


class ChallengePublic(BaseModel):
    """Challenge as sent to the browser: question + options, NO answer."""

    id: str
    type: ChallengeType
    track: Track
    difficulty: int
    payload: Dict[str, Any]
    # Per-challenge progress, populated when resuming a run.
    attempts_used: int = 0
    resolved: bool = False
    correct: Optional[bool] = None
    explanation: Optional[str] = None  # only present once resolved


# --------------------------------------------------------------------------- #
# API request / response bodies                                               #
# --------------------------------------------------------------------------- #
class DailyResponse(BaseModel):
    date: str
    track: Track
    stack_id: str
    attempts_per_challenge: int
    started_at: str
    completed: bool
    challenges: List[ChallengePublic]


class SubmitRequest(BaseModel):
    date: str
    track: Track
    challenge_id: str
    answer_payload: Dict[str, Any]
    client_elapsed_ms: int = 0


class SubmitResponse(BaseModel):
    correct: bool
    resolved: bool
    attempts_remaining: int
    score: Optional[int] = None  # per-challenge score, once resolved
    explanation: Optional[str] = None  # revealed once resolved


class CompleteRequest(BaseModel):
    date: str
    track: Track


class TrackXp(BaseModel):
    track: Track
    xp_before: int
    xp_after: int
    xp_delta: int
    level_before: int
    level_after: int


class ChallengeResult(BaseModel):
    challenge_id: str
    type: ChallengeType
    correct: bool
    attempts: int
    score: int
    elapsed_ms: int


class StreakInfo(BaseModel):
    current: int
    longest: int
    freezes_available: int
    last_played_date: Optional[str] = None
    freeze_used: bool = False


class CompleteResponse(BaseModel):
    date: str
    track: Track
    score: int
    total_ms: int
    results: List[ChallengeResult]
    streak: StreakInfo
    xp: TrackXp
    quarantined: bool
    leaderboard_rank: Optional[int] = None


class LeaderboardEntry(BaseModel):
    rank: int
    uid: str
    handle: str
    score: int
    total_ms: int
    track: Track
    is_me: bool = False


class LeaderboardResponse(BaseModel):
    date: str
    scope: str
    entries: List[LeaderboardEntry]
    me: Optional[LeaderboardEntry] = None


class MeResponse(BaseModel):
    uid: str
    handle: str
    display_name: str
    anonymous: bool
    created_at: str
    streak: StreakInfo
    tracks: Dict[str, Dict[str, int]]  # {track: {xp, level}}
