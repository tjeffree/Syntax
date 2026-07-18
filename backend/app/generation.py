"""OpenAI generation and validation for immutable daily challenge stacks."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .content import ContentError, Challenge, validate_raw_challenge

PROMPT_VERSION = "daily-stack-v1"
REQUIRED_TYPES = ("bug-spot", "parsons", "big-o")
TRACKS = ("python", "javascript")

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "challenges": {"type": "array", "minItems": 6, "maxItems": 6, "items": {"type": "object"}}
    },
    "required": ["challenges"],
    "additionalProperties": False,
}


def _prompt(game_date: str, existing_fingerprints: list[str], settings: Settings) -> str:
    avoid = "\n".join(existing_fingerprints[:50]) or "(none)"
    challenge_schema = Path(settings.schema_file).read_text(encoding="utf-8")
    return f"""Create the complete daily Syntax game stack for {game_date}.
Return exactly six challenge objects: one bug-spot, one parsons, and one big-o
for each of python and javascript. Use the exact field names and conventions in
the JSON schema below. Set each object's "id" to "{game_date}-<track>-<type>"
(for example "{game_date}-python-bug-spot") and, if you include "game_date", set
it to "{game_date}". Every object must include a server-only answer and a
short, accurate explanation. Challenges must be solvable from their payload,
have one unambiguous answer, and be distinct from the recent fingerprints below.

Enforce these constraints exactly, or the stack is rejected:
- bug-spot: answer.line is a 1-based line number that exists within payload.code.
- big-o: answer.correct is one of payload.options, verbatim.
- parsons: payload.maxIndent must be at least the deepest indent used in
  answer.solution, and answer.solution ids must match payload.blocks ids exactly.

Challenge schema:
{challenge_schema}

Recent fingerprints to avoid:
{avoid}
"""


def generate_raw_stack(game_date: str, settings: Settings | None = None, *, existing_fingerprints: list[str] | None = None) -> list[dict[str, Any]]:
    """Call the Responses API once and return untrusted candidate objects."""
    settings = settings or get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to generate daily content")
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": "You author precise, original programming micro-challenges. Return JSON only."},
            {"role": "user", "content": _prompt(game_date, existing_fingerprints or [], settings)},
        ],
        text={"format": {"type": "json_schema", "name": "daily_challenge_stack", "schema": OUTPUT_SCHEMA, "strict": False}},
    )
    try:
        parsed = json.loads(response.output_text)
        return parsed["challenges"]
    except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("OpenAI response did not contain a valid challenge stack") from exc


def fingerprint(raw: dict[str, Any]) -> str:
    """A deterministic exact-duplicate guard, not a semantic similarity claim."""
    payload = raw.get("payload", {})
    text = " ".join(str(payload.get(key, "")) for key in ("code", "prompt", "blocks"))
    text = re.sub(r"\s+", " ", text.strip().lower())
    return f"{raw.get('track')}:{raw.get('type')}:{text[:500]}"


def _fit_parsons_indent(raw: dict[str, Any]) -> dict[str, Any]:
    """Widen a generated Parsons payload's maxIndent to fit its own solution.

    maxIndent bounds how far the player can indent a block in the UI, so a
    solution that indents deeper than maxIndent is literally unreachable and
    would ship a broken puzzle. The solution is the authority on the depth the
    code requires, so raise the constraint to fit it rather than reject
    otherwise-valid code. Only widens, never narrows; non-Parsons pass through.
    """
    if raw.get("type") != "parsons":
        return raw
    solution = (raw.get("answer") or {}).get("solution") or []
    deepest = max((int(s.get("indent", 0)) for s in solution), default=0)
    payload = raw.get("payload") or {}
    if deepest > int(payload.get("maxIndent", 0)):
        raw = dict(raw)
        raw["payload"] = {**payload, "maxIndent": deepest}
    return raw


def validate_daily_stack(raw_challenges: list[dict[str, Any]], game_date: str, settings: Settings | None = None, *, existing_fingerprints: set[str] | None = None) -> list[Challenge]:
    """Apply local schema, semantic, layout, ID, and duplicate release gates."""
    settings = settings or get_settings()
    if len(raw_challenges) != 6:
        raise ContentError("daily stack must contain exactly six challenges")

    expected = Counter((track, challenge_type) for track in TRACKS for challenge_type in REQUIRED_TYPES)
    seen_ids: set[str] = set()
    seen_fingerprints = set(existing_fingerprints or set())
    validated: list[Challenge] = []
    for raw in raw_challenges:
        if raw.get("game_date") not in (None, game_date):
            raise ContentError("generated challenge has a mismatched game_date")
        raw = dict(raw)
        raw.pop("game_date", None)  # not part of the gameplay schema
        raw = _fit_parsons_indent(raw)  # accept valid code; widen maxIndent to fit
        challenge = validate_raw_challenge(raw, settings)
        # The id is derived data — fully determined by date, track, and type,
        # which are already enum-validated above — so assign it deterministically
        # rather than trust the model to reconstruct the exact composite string.
        # An unattended job can't retry a human, and a mismatch here was never a
        # content-quality signal, only a guess about string formatting.
        expected_id = f"{game_date}-{challenge.track}-{challenge.type}"
        challenge = challenge.model_copy(update={"id": expected_id})
        if challenge.id in seen_ids:
            raise ContentError(f"duplicate challenge id {challenge.id}")
        seen_ids.add(challenge.id)
        candidate_fingerprint = fingerprint(raw)
        if candidate_fingerprint in seen_fingerprints:
            raise ContentError(f"duplicate challenge content for {challenge.id}")
        seen_fingerprints.add(candidate_fingerprint)
        validated.append(challenge)

    actual = Counter((challenge.track, challenge.type) for challenge in validated)
    if actual != expected:
        raise ContentError("daily stack must have one required type for each track")
    return validated


def generate_valid_stack(
    game_date: str,
    settings: Settings | None = None,
    *,
    existing_fingerprints: set[str] | None = None,
    max_attempts: int = 3,
) -> list[dict[str, Any]]:
    """Generate a stack, regenerating on rejection up to ``max_attempts`` times.

    A single model call intermittently emits one challenge that violates a
    semantic gate (an unreachable Parsons indent, an out-of-range bug line).
    An unattended daily job has no human to re-run it, so a bad stack should
    self-heal within one execution rather than fail the whole day. The gates in
    :func:`validate_daily_stack` stay authoritative — we retry, never relax.
    """
    settings = settings or get_settings()
    fingerprints = set(existing_fingerprints or set())
    last_error: ContentError | None = None
    for attempt in range(1, max_attempts + 1):
        candidates = generate_raw_stack(game_date, settings, existing_fingerprints=sorted(fingerprints))
        try:
            validate_daily_stack(candidates, game_date, settings, existing_fingerprints=fingerprints)
            return candidates
        except ContentError as exc:
            last_error = exc
            print(f"stack {game_date}: attempt {attempt}/{max_attempts} rejected: {exc}")
    assert last_error is not None  # loop ran at least once, so a failure was recorded
    raise last_error


def challenge_document(challenge: Challenge, game_date: str, model: str) -> dict[str, Any]:
    document = challenge.model_dump(by_alias=True)
    document.update(
        {
            "game_date": game_date,
            "status": "approved",
            "generator": {"model": model, "prompt_version": PROMPT_VERSION},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return document
