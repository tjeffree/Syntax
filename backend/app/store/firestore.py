"""Cloud Firestore implementation of the Store interface.

Mirrors the data model in GDD §6. Only imported when STORE_MODE=firestore, so
local dev never needs the google-cloud dependencies configured.

Collections
-----------
users/{uid}
runs/{uid}_{date}_{track}
leaderboards/{date}_{track}/entries/{uid}
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..config import get_settings
from ..firestore_client import get_firestore_client
from .base import Store


class FirestoreStore(Store):
    def __init__(self) -> None:
        settings = get_settings()
        self._db = get_firestore_client(settings)

    @staticmethod
    def _run_key(uid: str, date: str, track: str) -> str:
        return f"{uid}_{date}_{track}"

    @staticmethod
    def _lb_doc(date: str, track: str) -> str:
        return f"{date}_{track}"

    # --- users ---------------------------------------------------------- #
    def get_user(self, uid: str) -> Optional[Dict]:
        snap = self._db.collection("users").document(uid).get()
        return snap.to_dict() if snap.exists else None

    def save_user(self, user: Dict) -> None:
        self._db.collection("users").document(user["uid"]).set(user)

    # --- runs ----------------------------------------------------------- #
    def get_run(self, uid: str, date: str, track: str) -> Optional[Dict]:
        snap = self._db.collection("runs").document(self._run_key(uid, date, track)).get()
        return snap.to_dict() if snap.exists else None

    def save_run(self, run: Dict) -> None:
        key = self._run_key(run["uid"], run["date"], run["track"])
        self._db.collection("runs").document(key).set(run)

    # --- leaderboards --------------------------------------------------- #
    def upsert_leaderboard_entry(self, date: str, track: str, entry: Dict) -> None:
        (
            self._db.collection("leaderboards")
            .document(self._lb_doc(date, track))
            .collection("entries")
            .document(entry["uid"])
            .set(entry)
        )

    def get_leaderboard(self, date: str, track: str) -> List[Dict]:
        docs = (
            self._db.collection("leaderboards")
            .document(self._lb_doc(date, track))
            .collection("entries")
            .stream()
        )
        return [d.to_dict() for d in docs]
