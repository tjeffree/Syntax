from __future__ import annotations

import pytest

from app.content import ContentError
from app.generation import challenge_document, fingerprint, validate_daily_stack


DATE = "2026-07-19"


def _challenge(track: str, challenge_type: str) -> dict:
    challenge_id = f"{DATE}-{track}-{challenge_type}"
    base = {
        "id": challenge_id,
        "type": challenge_type,
        "track": track,
        "difficulty": 2,
        "skillNodes": ["basics"],
        "explanation": "The answer follows directly from the code.",
    }
    if challenge_type == "bug-spot":
        return base | {"payload": {"language": track, "code": "x = 1\nprint(x)"}, "answer": {"line": 2}}
    if challenge_type == "parsons":
        return base | {
            "payload": {"language": track, "indent": False, "maxIndent": 0, "blocks": [{"id": "a", "code": "x = 1"}, {"id": "b", "code": "print(x)"}]},
            "answer": {"solution": [{"id": "a", "indent": 0}, {"id": "b", "indent": 0}]},
        }
    return base | {
        "payload": {"language": track, "code": "for i in range(n):\n    print(i)", "prompt": "time", "options": ["O(1)", "O(n)", "O(n²)"]},
        "answer": {"correct": "O(n)"},
    }


def _stack() -> list[dict]:
    return [_challenge(track, challenge_type) for track in ("python", "javascript") for challenge_type in ("bug-spot", "parsons", "big-o")]


def test_generated_stack_is_valid_and_keeps_gameplay_schema(env):
    challenges = validate_daily_stack(_stack(), DATE)
    assert len(challenges) == 6
    document = challenge_document(challenges[0], DATE, "test-model")
    assert document["status"] == "approved"
    assert document["answer"]


def test_generated_stack_rejects_duplicate_content(env):
    candidates = _stack()
    with pytest.raises(ContentError, match="duplicate challenge content"):
        validate_daily_stack(candidates, DATE, existing_fingerprints={fingerprint(candidates[0])})


def test_generated_stack_rejects_wrong_id(env):
    candidates = _stack()
    candidates[0]["id"] = "wrong-id"
    with pytest.raises(ContentError, match="challenge id must be"):
        validate_daily_stack(candidates, DATE)
