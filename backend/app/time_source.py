"""Single source of truth for "server now".

The score clock is server-side (GDD §8.2). Centralising time access lets tests
freeze the clock via the SYNTAX_NOW env var without touching real time.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .config import get_settings


def now() -> datetime:
    override = get_settings().syntax_now
    if override:
        # Accept a trailing "Z".
        return datetime.fromisoformat(override.replace("Z", "+00:00")).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def now_ms() -> int:
    return int(now().timestamp() * 1000)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
