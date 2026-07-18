"""Challenge content: loading, schema validation, and answer grading.

Challenges are authored as JSON (GDD §2 content pipeline) and validated against
`schema/challenge.schema.json` both here at startup and in CI. Grading is the
single server-side authority on correctness (GDD §8.1).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from jsonschema import Draft202012Validator

from .config import Settings, get_settings
from .models import Challenge


class ContentError(ValueError):
    """Raised when authored content is structurally invalid."""


def _load_schema(settings: Settings) -> Draft202012Validator:
    schema = json.loads(Path(settings.schema_file).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _semantic_checks(raw: Dict) -> List[str]:
    """Cross-field checks the JSON schema can't express.

    A broken 'correct answer' is the fastest way to lose a developer audience
    (GDD §2), so we fail loudly at load time.
    """
    errors: List[str] = []
    ctype = raw["type"]
    payload = raw["payload"]
    answer = raw["answer"]

    if ctype == "bug-spot":
        n_lines = len(payload["code"].splitlines())
        if not (1 <= answer["line"] <= n_lines):
            errors.append(f"answer.line {answer['line']} outside 1..{n_lines}")

    elif ctype == "big-o":
        if answer["correct"] not in payload["options"]:
            errors.append("answer.correct is not among payload.options")

    elif ctype == "parsons":
        block_ids = [b["id"] for b in payload["blocks"]]
        sol_ids = [s["id"] for s in answer["solution"]]
        if sorted(block_ids) != sorted(sol_ids):
            errors.append("answer.solution ids do not match payload.blocks ids")
        if len(set(block_ids)) != len(block_ids):
            errors.append("payload.blocks has duplicate ids")
        max_indent = payload.get("maxIndent", 0)
        for s in answer["solution"]:
            if s["indent"] > max_indent:
                errors.append(f"solution indent {s['indent']} exceeds maxIndent {max_indent}")
    return errors


def validate_raw_challenge(raw: Dict, settings: Settings | None = None) -> Challenge:
    """Validate one generated or authored challenge before it is persisted."""
    settings = settings or get_settings()
    errors = sorted(_load_schema(settings).iter_errors(raw), key=lambda e: e.path)
    if errors:
        raise ContentError("schema invalid: " + "; ".join(e.message for e in errors))
    semantic_errors = _semantic_checks(raw)
    if semantic_errors:
        raise ContentError("; ".join(semantic_errors))
    return Challenge(**raw)


def load_all(settings: Settings) -> List[Challenge]:
    validator = _load_schema(settings)
    content_dir = Path(settings.content_dir)
    if not content_dir.exists():
        raise ContentError(f"content dir not found: {content_dir}")

    challenges: List[Challenge] = []
    seen_ids: set[str] = set()
    for path in sorted(content_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            challenge = validate_raw_challenge(raw, settings)
        except ContentError as exc:
            raise ContentError(f"{path.name}: {exc}") from exc
        if raw["id"] in seen_ids:
            raise ContentError(f"{path.name}: duplicate challenge id {raw['id']}")
        seen_ids.add(raw["id"])
        challenges.append(challenge)
    if not challenges:
        raise ContentError(f"no challenges found in {content_dir}")
    return challenges


class ContentIndex:
    """In-memory index of loaded challenges."""

    def __init__(self, challenges: List[Challenge]) -> None:
        self.by_id: Dict[str, Challenge] = {c.id: c for c in challenges}
        self.by_track_type: Dict[Tuple[str, str], List[Challenge]] = {}
        for c in challenges:
            self.by_track_type.setdefault((c.track, c.type), []).append(c)
        # deterministic ordering within each bucket
        for bucket in self.by_track_type.values():
            bucket.sort(key=lambda c: c.id)

    def get(self, challenge_id: str) -> Challenge | None:
        return self.by_id.get(challenge_id)


@lru_cache
def get_content() -> ContentIndex:
    return ContentIndex(load_all(get_settings()))


# --------------------------------------------------------------------------- #
# Grading — the only place correctness is decided.                            #
# --------------------------------------------------------------------------- #
def grade(challenge: Challenge, submitted: Dict) -> bool:
    ctype = challenge.type
    answer = challenge.answer
    try:
        if ctype == "bug-spot":
            return int(submitted.get("line")) == int(answer["line"])

        if ctype == "big-o":
            return str(submitted.get("choice")) == str(answer["correct"])

        if ctype == "parsons":
            sol = answer["solution"]
            sub = submitted.get("solution")
            if not isinstance(sub, list) or len(sub) != len(sol):
                return False
            indent_matters = bool(challenge.payload.get("indent", False))
            for expected, got in zip(sol, sub):
                if str(got.get("id")) != str(expected["id"]):
                    return False
                if indent_matters and int(got.get("indent", 0)) != int(expected["indent"]):
                    return False
            return True
    except (TypeError, ValueError):
        return False
    return False
