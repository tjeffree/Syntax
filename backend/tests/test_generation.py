from __future__ import annotations

import pytest

import app.generation as gen
from app.content import ContentError
from app.generation import challenge_document, fingerprint, generate_valid_stack, validate_daily_stack


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


def test_generated_parsons_widens_maxindent_to_fit_solution(env):
    candidates = _stack()
    parsons = candidates[1]  # python parsons
    parsons["payload"]["indent"] = True
    parsons["payload"]["maxIndent"] = 2
    parsons["answer"]["solution"][1]["indent"] = 3  # deeper than declared maxIndent
    challenges = validate_daily_stack(candidates, DATE)
    py_parsons = next(c for c in challenges if c.track == "python" and c.type == "parsons")
    # Accepted, and maxIndent raised so the correct answer is reachable in the UI.
    assert py_parsons.payload["maxIndent"] == 3


def _bad_stack() -> list[dict]:
    stack = _stack()
    stack[0]["answer"]["line"] = 99  # bug-spot line outside the code -> rejected
    return stack


def test_generate_valid_stack_retries_until_valid(env, monkeypatch):
    attempts = {"n": 0}

    def fake_generate(game_date, settings=None, *, existing_fingerprints=None):
        attempts["n"] += 1
        return _bad_stack() if attempts["n"] == 1 else _stack()

    monkeypatch.setattr(gen, "generate_raw_stack", fake_generate)
    candidates = generate_valid_stack(DATE, max_attempts=3)
    assert attempts["n"] == 2  # regenerated once after the first stack was rejected
    assert len(candidates) == 6


def test_generate_valid_stack_gives_up_after_max_attempts(env, monkeypatch):
    attempts = {"n": 0}

    def fake_generate(game_date, settings=None, *, existing_fingerprints=None):
        attempts["n"] += 1
        return _bad_stack()

    monkeypatch.setattr(gen, "generate_raw_stack", fake_generate)
    with pytest.raises(ContentError):
        generate_valid_stack(DATE, max_attempts=2)
    assert attempts["n"] == 2  # bounded, does not loop forever
