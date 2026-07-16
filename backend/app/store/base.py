"""Abstract persistence interface.

Documents are plain JSON-serialisable dicts so the same shapes round-trip
through both the memory store and Firestore.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class Store(ABC):
    # --- users ---------------------------------------------------------- #
    @abstractmethod
    def get_user(self, uid: str) -> Optional[Dict]:
        ...

    @abstractmethod
    def save_user(self, user: Dict) -> None:
        ...

    # --- runs (one per uid+date+track) --------------------------------- #
    @abstractmethod
    def get_run(self, uid: str, date: str, track: str) -> Optional[Dict]:
        ...

    @abstractmethod
    def save_run(self, run: Dict) -> None:
        ...

    # --- leaderboards (per date+track) --------------------------------- #
    @abstractmethod
    def upsert_leaderboard_entry(self, date: str, track: str, entry: Dict) -> None:
        ...

    @abstractmethod
    def get_leaderboard(self, date: str, track: str) -> List[Dict]:
        ...
