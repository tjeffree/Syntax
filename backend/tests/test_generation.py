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


def test_generated_stack_normalizes_id_from_date_track_type(env):
    candidates = _stack()
    candidates[0]["id"] = "whatever-the-model-guessed"
    challenges = validate_daily_stack(candidates, DATE)
    # The id is derived deterministically, not taken from the model's output.
    assert challenges[0].id == f"{DATE}-{challenges[0].track}-{challenges[0].type}"


def test_generated_stack_rejects_duplicate_track_type(env):
    candidates = _stack()
    # Two challenges collapsing to the same (track, type) now collide on the
    # derived id, which the duplicate-id gate must still reject.
    candidates[1] = _challenge("python", "bug-spot")
    with pytest.raises(ContentError):
        validate_daily_stack(candidates, DATE)
