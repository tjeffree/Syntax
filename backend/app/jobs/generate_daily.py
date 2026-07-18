"""Generate and atomically publish a single future daily stack."""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from ..config import get_settings
from ..firestore_client import get_firestore_client
from ..generation import TRACKS, challenge_document, fingerprint, generate_raw_stack, validate_daily_stack


def _recent_fingerprints(db, retention_days: int) -> set[str]:
    # At the planned retention size this bounded scan is cheap and avoids a
    # composite index. It is an exact duplicate guard, not semantic search.
    fingerprints: set[str] = set()
    for snapshot in db.collection("challenges").stream():
        raw = snapshot.to_dict() or {}
        if raw.get("status") == "approved":
            fingerprints.add(fingerprint(raw))
    return fingerprints


def publish(game_date: str, candidates: list[dict], *, dry_run: bool = False) -> bool:
    settings = get_settings()
    db = get_firestore_client(settings)
    manifest_ref = db.collection("dailyStacks").document(game_date)
    existing = manifest_ref.get()
    if existing.exists and (existing.to_dict() or {}).get("status") == "published":
        return False

    fingerprints = _recent_fingerprints(db, settings.daily_stack_retention_days)
    challenges = validate_daily_stack(candidates, game_date, settings, existing_fingerprints=fingerprints)
    if dry_run:
        return True

    from google.cloud import firestore

    transaction = db.transaction()

    @firestore.transactional
    def write(transaction):
        current = manifest_ref.get(transaction=transaction)
        if current.exists and (current.to_dict() or {}).get("status") == "published":
            return False
        tracks = {track: [] for track in TRACKS}
        for challenge in challenges:
            tracks[challenge.track].append(challenge.id)
            transaction.set(
                db.collection("challenges").document(challenge.id),
                challenge_document(challenge, game_date, settings.openai_model),
            )
        transaction.set(manifest_ref, {
            "game_date": game_date,
            "status": "published",
            "tracks": tracks,
            "generation_id": game_date,
            "schema_version": 1,
            "published_at": firestore.SERVER_TIMESTAMP,
        })
        return True

    return write(transaction)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=(date.today() + timedelta(days=1)).isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    db = get_firestore_client(settings)
    fingerprints = sorted(_recent_fingerprints(db, settings.daily_stack_retention_days))
    candidates = generate_raw_stack(args.date, settings, existing_fingerprints=fingerprints)
    changed = publish(args.date, candidates, dry_run=args.dry_run)
    print(f"daily stack {args.date}: {'validated' if args.dry_run else ('published' if changed else 'already published')}")


if __name__ == "__main__":
    main()
