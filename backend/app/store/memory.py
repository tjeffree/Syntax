"""File-backed in-memory store for local dev and CI.

State is kept in a nested dict and flushed to a JSON file after every mutation.
Not concurrency-safe across processes — which is fine for a single uvicorn dev
server. Swap in FirestoreStore for anything real.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from .base import Store


class MemoryStore(Store):
    def __init__(self, data_file: str) -> None:
        self._path = Path(data_file)
        self._lock = threading.RLock()
        self._data: Dict = {"users": {}, "runs": {}, "leaderboards": {}}
        self._load()

    # --- persistence ---------------------------------------------------- #
    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        for key in ("users", "runs", "leaderboards"):
            self._data.setdefault(key, {})

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    @staticmethod
    def _run_key(uid: str, date: str, track: str) -> str:
        return f"{uid}_{date}_{track}"

    @staticmethod
    def _lb_key(date: str, track: str) -> str:
        return f"{date}_{track}"

    # --- users ---------------------------------------------------------- #
    def get_user(self, uid: str) -> Optional[Dict]:
        with self._lock:
            u = self._data["users"].get(uid)
            return json.loads(json.dumps(u)) if u else None

    def save_user(self, user: Dict) -> None:
        with self._lock:
            self._data["users"][user["uid"]] = user
            self._flush()

    # --- runs ----------------------------------------------------------- #
    def get_run(self, uid: str, date: str, track: str) -> Optional[Dict]:
        with self._lock:
            r = self._data["runs"].get(self._run_key(uid, date, track))
            return json.loads(json.dumps(r)) if r else None

    def save_run(self, run: Dict) -> None:
        with self._lock:
            key = self._run_key(run["uid"], run["date"], run["track"])
            self._data["runs"][key] = run
            self._flush()

    # --- leaderboards --------------------------------------------------- #
    def upsert_leaderboard_entry(self, date: str, track: str, entry: Dict) -> None:
        with self._lock:
            board = self._data["leaderboards"].setdefault(self._lb_key(date, track), {})
            board[entry["uid"]] = entry
            self._flush()

    def get_leaderboard(self, date: str, track: str) -> List[Dict]:
        with self._lock:
            board = self._data["leaderboards"].get(self._lb_key(date, track), {})
            return json.loads(json.dumps(list(board.values())))
