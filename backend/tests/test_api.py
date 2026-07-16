"""End-to-end API flow over the dev/memory stack."""
from __future__ import annotations

from app.content import get_content
from .conftest import AUTH

DATE = "2026-07-16"
TRACK = "python"


def _correct_payload(cid: str) -> dict:
    c = get_content().get(cid)
    if c.type == "bug-spot":
        return {"line": c.answer["line"]}
    if c.type == "big-o":
        return {"choice": c.answer["correct"]}
    return {"solution": c.answer["solution"]}


def test_requires_auth(client):
    assert client.get(f"/daily/{DATE}?track={TRACK}").status_code == 401
    assert client.get(f"/daily/{DATE}?track={TRACK}", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_daily_hides_answers(client):
    r = client.get(f"/daily/{DATE}?track={TRACK}", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["track"] == TRACK
    assert len(body["challenges"]) == 3
    for ch in body["challenges"]:
        assert "answer" not in ch
        assert ch["resolved"] is False
        assert ch["explanation"] is None


def test_full_happy_path(client, env):
    set_now = env
    r = client.get(f"/daily/{DATE}?track={TRACK}", headers=AUTH)
    challenges = r.json()["challenges"]

    for i, ch in enumerate(challenges, start=1):
        set_now(f"2026-07-16T09:00:{i * 5:02d}Z")
        resp = client.post(
            "/submit",
            headers=AUTH,
            json={
                "date": DATE,
                "track": TRACK,
                "challenge_id": ch["id"],
                "answer_payload": _correct_payload(ch["id"]),
                "client_elapsed_ms": 4200,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["correct"] is True
        assert data["resolved"] is True
        assert data["score"] > 0
        assert data["explanation"]  # revealed on resolution

    set_now("2026-07-16T09:00:30Z")
    done = client.post("/complete", headers=AUTH, json={"date": DATE, "track": TRACK})
    assert done.status_code == 200, done.text
    result = done.json()
    assert result["score"] > 0
    assert result["quarantined"] is False
    assert result["leaderboard_rank"] == 1
    assert result["xp"]["xp_delta"] > 0
    assert result["streak"]["current"] == 1

    # Leaderboard shows me at rank 1.
    lb = client.get(f"/leaderboard/{DATE}?track={TRACK}", headers=AUTH).json()
    assert lb["me"]["rank"] == 1
    assert len(lb["entries"]) == 1

    # /me reflects XP and streak.
    me = client.get("/me", headers=AUTH).json()
    assert me["tracks"][TRACK]["xp"] == result["xp"]["xp_after"]
    assert me["streak"]["current"] == 1


def test_second_attempt_then_fail_reveals_explanation(client, env):
    set_now = env
    r = client.get(f"/daily/{DATE}?track={TRACK}", headers=AUTH)
    ch = r.json()["challenges"][0]
    wrong = {"line": 999} if get_content().get(ch["id"]).type == "bug-spot" else {"choice": "O(nope)", "solution": []}

    first = client.post(
        "/submit",
        headers=AUTH,
        json={"date": DATE, "track": TRACK, "challenge_id": ch["id"], "answer_payload": wrong},
    ).json()
    assert first["correct"] is False and first["resolved"] is False
    assert first["attempts_remaining"] == 1

    second = client.post(
        "/submit",
        headers=AUTH,
        json={"date": DATE, "track": TRACK, "challenge_id": ch["id"], "answer_payload": wrong},
    ).json()
    assert second["correct"] is False and second["resolved"] is True
    assert second["score"] == 0
    assert second["explanation"]  # learn something even on failure (GDD §1)

    # A third submit is rejected (attempt cap enforced server-side, GDD §8.3).
    third = client.post(
        "/submit",
        headers=AUTH,
        json={"date": DATE, "track": TRACK, "challenge_id": ch["id"], "answer_payload": wrong},
    )
    assert third.status_code == 400


def test_complete_is_idempotent(client, env):
    set_now = env
    challenges = client.get(f"/daily/{DATE}?track={TRACK}", headers=AUTH).json()["challenges"]
    for i, ch in enumerate(challenges, start=1):
        set_now(f"2026-07-16T09:00:{i * 5:02d}Z")
        client.post(
            "/submit",
            headers=AUTH,
            json={"date": DATE, "track": TRACK, "challenge_id": ch["id"], "answer_payload": _correct_payload(ch["id"])},
        )
    first = client.post("/complete", headers=AUTH, json={"date": DATE, "track": TRACK}).json()
    second = client.post("/complete", headers=AUTH, json={"date": DATE, "track": TRACK}).json()
    assert first["score"] == second["score"]
    assert first["streak"]["current"] == second["streak"]["current"] == 1

    # XP was applied once, not twice.
    me = client.get("/me", headers=AUTH).json()
    assert me["tracks"][TRACK]["xp"] == first["xp"]["xp_after"]


def test_complete_requires_full_stack(client):
    client.get(f"/daily/{DATE}?track={TRACK}", headers=AUTH)
    r = client.post("/complete", headers=AUTH, json={"date": DATE, "track": TRACK})
    assert r.status_code == 400
