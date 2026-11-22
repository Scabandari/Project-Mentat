from typing import Any

import httpx

from tests.conftest import Clock

API = "/api/v1"


async def _deck_id(client: httpx.AsyncClient, slug: str) -> str:
    pack = (await client.get(f"{API}/packs/poker-math")).json()
    return str(next(d["id"] for d in pack["decks"] if d["slug"] == slug))


async def _session(client: httpx.AsyncClient, **body: Any) -> dict[str, Any]:
    r = await client.post(f"{API}/sessions", json=body)
    assert r.status_code == 201, r.text
    return dict(r.json())


async def _next(client: httpx.AsyncClient, sid: str) -> dict[str, Any]:
    r = await client.post(f"{API}/sessions/{sid}/next")
    assert r.status_code == 200, r.text
    return dict(r.json())


async def _answer(
    client: httpx.AsyncClient, iid: str, rating: str = "good", latency: int = 3000
) -> httpx.Response:
    return await client.post(
        f"{API}/instances/{iid}/answer", json={"self_rating": rating, "latency_ms": latency}
    )


async def test_flip_review_flow(client: httpx.AsyncClient) -> None:
    deck = await _deck_id(client, "combinatorics")
    s = await _session(client, deck_ids=[deck], new_limit=3)
    assert s["new_count"] == 3 and s["due_count"] == 0

    first = await _next(client, s["id"])
    assert first["queue"] == {"due": 0, "new": 3, "reviewed": 0}  # includes the card on screen
    p = first["problem"]
    assert p["answer_type"] == "flip" and p["is_new"] is True
    assert p["deck_slug"] == "combinatorics"
    assert p["back_md"]  # self-graded flip cards carry their back for the reveal

    # next is idempotent until answered
    again = await _next(client, s["id"])
    assert again["problem"]["instance_id"] == p["instance_id"]

    r = await _answer(client, p["instance_id"], "easy")
    assert r.status_code == 200, r.text
    grade = r.json()
    assert grade["rating"] == "easy" and grade["is_correct"] is None
    assert grade["back_md"] and grade["next_due"]

    # double answer rejected with error envelope
    dup = await _answer(client, p["instance_id"])
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "http_409"

    second = (await _next(client, s["id"]))["problem"]
    assert second["card_id"] != p["card_id"]


async def test_new_limit_and_learn_ahead(client: httpx.AsyncClient, clock: Clock) -> None:
    deck = await _deck_id(client, "combinatorics")
    s = await _session(client, deck_ids=[deck], new_limit=1)

    p = (await _next(client, s["id"]))["problem"]
    assert (await _answer(client, p["instance_id"], "again")).status_code == 200

    # new limit hit; the failed card is in learning (due in ~1 min) → shown via learn-ahead
    nxt = await _next(client, s["id"])
    assert nxt["problem"]["card_id"] == p["card_id"]
    assert nxt["problem"]["is_new"] is False
    assert nxt["queue"]["new"] == 0

    r = await _answer(client, nxt["problem"]["instance_id"], "easy")
    assert r.status_code == 200
    done = await _next(client, s["id"])
    assert done["problem"] is None and done["queue"]["reviewed"] == 2


async def test_due_cards_come_back(client: httpx.AsyncClient, clock: Clock) -> None:
    deck = await _deck_id(client, "combinatorics")
    s = await _session(client, deck_ids=[deck], new_limit=1)
    p = (await _next(client, s["id"]))["problem"]
    grade = (await _answer(client, p["instance_id"], "easy")).json()
    await client.post(f"{API}/sessions/{s['id']}/end")

    clock.advance(days=60)
    pack = (await client.get(f"{API}/packs/poker-math")).json()
    assert next(d for d in pack["decks"] if d["id"] == deck)["due_count"] == 1

    s2 = await _session(client, deck_ids=[deck], new_limit=0)
    assert s2["due_count"] == 1
    p2 = (await _next(client, s2["id"]))["problem"]
    assert p2["card_id"] == p["card_id"] and grade["next_due"]


async def test_daily_new_limit_from_settings(client: httpx.AsyncClient) -> None:
    r = await client.patch(f"{API}/me/settings", json={"daily_new_limit": 2})
    assert r.json()["daily_new_limit"] == 2

    s = await _session(client)
    assert s["new_count"] == 2
    for _ in range(2):
        p = (await _next(client, s["id"]))["problem"]
        await _answer(client, p["instance_id"], "easy")
    assert (await _next(client, s["id"]))["problem"] is None

    # a new review session the same day gets no new cards
    assert (await _session(client))["new_count"] == 0


async def test_drill_does_not_touch_schedule(client: httpx.AsyncClient) -> None:
    deck = await _deck_id(client, "combinatorics")
    s = await _session(client, mode="drill", deck_ids=[deck])
    seen = set()
    for _ in range(4):
        p = (await _next(client, s["id"]))["problem"]
        seen.add(p["card_id"])
        grade = (await _answer(client, p["instance_id"], "good")).json()
        assert grade["next_due"] is None
    assert len(seen) > 1

    pack = (await client.get(f"{API}/packs/poker-math")).json()
    combos = next(d for d in pack["decks"] if d["id"] == deck)
    assert combos["new_count"] == combos["card_count"]


async def test_flip_requires_self_rating(client: httpx.AsyncClient) -> None:
    s = await _session(client, new_limit=1)
    p = (await _next(client, s["id"]))["problem"]
    r = await client.post(f"{API}/instances/{p['instance_id']}/answer", json={"latency_ms": 1})
    assert r.status_code == 422


async def test_summary(client: httpx.AsyncClient, clock: Clock) -> None:
    s = await _session(client, new_limit=3)
    for rating in ["good", "again", "easy"]:
        p = (await _next(client, s["id"]))["problem"]
        await _answer(client, p["instance_id"], rating, latency=2000)
        clock.advance(seconds=10)
    summary = (await client.post(f"{API}/sessions/{s['id']}/end")).json()
    assert summary["reviewed"] == 3
    assert summary["correct"] == 2
    assert summary["median_latency_ms"] == 2000
    assert summary["duration_s"] == 30

    ended = await client.post(f"{API}/sessions/{s['id']}/next")
    assert ended.status_code == 409


async def test_settings_validation(client: httpx.AsyncClient) -> None:
    assert (await client.get(f"{API}/me/settings")).json()["stakes_format"] == "online"
    r = await client.patch(f"{API}/me/settings", json={"stakes_format": "live"})
    assert r.json()["stakes_format"] == "live"
    for bad in ({"timezone": "Mars/Base"}, {"daily_new_limit": 500}):
        assert (await client.patch(f"{API}/me/settings", json=bad)).status_code == 422


async def test_unknown_session_404(client: httpx.AsyncClient) -> None:
    r = await client.post(f"{API}/sessions/00000000-0000-0000-0000-000000000000/next")
    assert r.status_code == 404
