"""Content loads, validates, and grades correctly."""
from __future__ import annotations

from app.config import get_settings
from app.content import get_content, grade


def test_all_content_loads(env):
    index = get_content()
    assert len(index.by_id) >= 12
    # Both tracks have all three launch types (GDD §9 Phase 1).
    for track in ("python", "javascript"):
        for ctype in ("bug-spot", "parsons", "big-o"):
            assert index.by_track_type.get((track, ctype)), f"missing {track}/{ctype}"


def test_grade_bug_spot(env):
    c = get_content().get("py-bug-001")
    assert grade(c, {"line": 5}) is True
    assert grade(c, {"line": 4}) is False
    assert grade(c, {}) is False


def test_grade_big_o(env):
    c = get_content().get("py-bigo-001")
    assert grade(c, {"choice": "O(log n)"}) is True
    assert grade(c, {"choice": "O(n)"}) is False


def test_grade_parsons_order_and_indent(env):
    c = get_content().get("py-parsons-002")
    correct = {"solution": c.answer["solution"]}
    assert grade(c, correct) is True
    # wrong order
    shuffled = {"solution": list(reversed(c.answer["solution"]))}
    assert grade(c, shuffled) is False
    # right order, wrong indent
    bad_indent = {"solution": [{"id": s["id"], "indent": 0} for s in c.answer["solution"]]}
    assert grade(c, bad_indent) is False


def test_public_payload_has_no_answer(env):
    c = get_content().get("py-bug-001")
    pub = c.public_payload().model_dump()
    assert "answer" not in pub
    assert pub["explanation"] is None
