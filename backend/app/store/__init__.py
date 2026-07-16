"""Persistence layer.

`Store` is the abstract interface used by the routers. Two implementations:

* ``MemoryStore``    — JSON file on disk. Zero external dependencies; powers
                       local dev and CI.
* ``FirestoreStore`` — Cloud Firestore via the Firebase Admin SDK, matching the
                       data model in GDD §6.

The active implementation is chosen by ``STORE_MODE`` and cached as a singleton.
"""
from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from .base import Store
from .memory import MemoryStore


@lru_cache
def get_store() -> Store:
    settings = get_settings()
    if settings.store_mode == "firestore":
        from .firestore import FirestoreStore

        return FirestoreStore()
    return MemoryStore(settings.data_file)


__all__ = ["Store", "MemoryStore", "get_store"]
