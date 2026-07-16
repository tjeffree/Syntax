"""Universal daily seed (GDD §4).

Every player on the same local calendar date + track gets the exact same stack.
Selection is a deterministic hash of (date, track, type) so it's stable across
processes and restarts — no stored schedule needed for the MVP.
"""
from __future__ import annotations

import hashlib
from typing import List, Tuple

from .content import ContentIndex

# One of each launch type, in a fixed presentation order (GDD §9 Phase 1).
STACK_TYPES = ["bug-spot", "parsons", "big-o"]


def _seed_int(*parts: str) -> int:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    return int(digest, 16)


def build_stack(index: ContentIndex, date: str, track: str) -> Tuple[str, List[str]]:
    """Return (stack_id, [challenge_id, ...]) for a given date + track."""
    ids: List[str] = []
    for ctype in STACK_TYPES:
        bucket = index.by_track_type.get((track, ctype), [])
        if not bucket:
            continue  # skip a type with no authored content for this track
        pick = _seed_int(date, track, ctype) % len(bucket)
        ids.append(bucket[pick].id)
    return f"{date}:{track}", ids
