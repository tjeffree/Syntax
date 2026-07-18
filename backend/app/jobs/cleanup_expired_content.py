"""Delete expired generated stack manifests and their private challenges."""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from ..config import get_settings
from ..firestore_client import get_firestore_client


def cleanup(*, dry_run: bool = False) -> int:
    settings = get_settings()
    db = get_firestore_client(settings)
    cutoff = (date.today() - timedelta(days=settings.daily_stack_retention_days)).isoformat()
    expired = []
    for snapshot in db.collection("dailyStacks").stream():
        manifest = snapshot.to_dict() or {}
        if manifest.get("status") == "published" and manifest.get("game_date", snapshot.id) < cutoff:
            expired.append((snapshot.reference, manifest))
    if dry_run:
        return len(expired)
    batch = db.batch()
    for manifest_ref, manifest in expired:
        for ids in (manifest.get("tracks") or {}).values():
            for challenge_id in ids:
                batch.delete(db.collection("challenges").document(challenge_id))
        batch.delete(manifest_ref)
    if expired:
        batch.commit()
    return len(expired)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(f"expired stacks {'found' if args.dry_run else 'deleted'}: {cleanup(dry_run=args.dry_run)}")


if __name__ == "__main__":
    main()
