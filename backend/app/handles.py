"""Stable, privacy-preserving display handles.

Players are identified on the leaderboard and in the UI by a generated handle
(e.g. ``async-otter-4f2a``), never their real Google/GitHub name. The handle is
derived deterministically from the uid so it is:

* stable across sessions and devices (same uid → same handle);
* preserved automatically when an anonymous account is upgraded in place
  (linking keeps the uid), and consistent when a returning player signs into an
  existing account;
* free of any store round-trip or collision-checking scan.

The trailing hash segment makes same-word collisions between two different uids
astronomically unlikely without a uniqueness scan.
"""
from __future__ import annotations

import hashlib

_ADJECTIVES = [
    "async", "atomic", "binary", "brave", "cached", "clever", "cosmic",
    "crimson", "curried", "eager", "elastic", "fuzzy", "golden", "hidden",
    "idle", "immutable", "lazy", "lucid", "mellow", "nimble", "noble",
    "polar", "prime", "quiet", "rapid", "rusty", "scarlet", "silent",
    "solar", "stoic", "swift", "tidal", "vivid", "witty",
]

_NOUNS = [
    "badger", "cipher", "comet", "falcon", "ferret", "gecko", "heron",
    "ibex", "jaguar", "kernel", "lambda", "lemur", "lynx", "magpie",
    "marmot", "monad", "narwhal", "ocelot", "otter", "packet", "panther",
    "puffin", "raptor", "raven", "socket", "sparrow", "stingray", "tapir",
    "vector", "walrus", "weasel", "wombat",
]


def generate_handle(uid: str) -> str:
    """A stable ``adjective-noun-hex`` handle derived from a uid."""
    digest = hashlib.sha256(uid.encode("utf-8")).digest()
    adjective = _ADJECTIVES[digest[0] % len(_ADJECTIVES)]
    noun = _NOUNS[digest[1] % len(_NOUNS)]
    suffix = digest[2:4].hex()  # 4 hex chars → 65k, collision-safe in practice
    return f"{adjective}-{noun}-{suffix}"
