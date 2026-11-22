import httpx
import pytest

from tests.conftest import Clock
from tests.test_study import API, _answer, _deck_id, _next, _session


async def _review(client: httpx.AsyncClient, deck: str, ratings: list[str]) -> None:
    s = await _session(client, deck_ids=[deck], new_limit=len(ratings))
    for rating in ratings:
        p = (await _next(client, s["id"]))["problem"]
        await _answer(client, p["instance_id"], rating, latency=2000)
    await client.post(f"{API}/sessions/{s['id']}/end")


async def test_empty_overview(client: httpx.AsyncClient) -> None:
    o = (await client.get(f"{API}/stats/overview")).json()
    assert o["streak_days"] == 0 and o["reviews_7d"] == 0
    assert o["accuracy_7d"] is None and len(o["daily"]) == 14
    assert o["decks"] == [] and o["weakest"] == []


@pytest.mark.usefixtures("static_only")
async def test_overview_streak_and_weakest(client: httpx.AsyncClient, clock: Clock) -> None:
    await client.patch(f"{API}/me/settings", json={"daily_new_limit": 100})
    combos = await _deck_id(client, "combinatorics")
    outs = await _deck_id(client, "outs-and-draws")

    await _review(client, combos, ["good"] * 5)
    clock.advance(days=1)
    await _review(client, outs, ["again", "again", "again", "good", "good"])
    clock.advance(days=1)
    await _review(client, combos, ["good"])

    o = (await client.get(f"{API}/stats/overview")).json()
    assert o["streak_days"] == 3
    assert o["reviews_today"] == 1
    assert o["reviews_7d"] == 11
    assert o["accuracy_7d"] == pytest.approx(8 / 11, abs=0.001)
    assert o["median_latency_ms_7d"] == 2000
    assert [d["reviews"] for d in o["daily"][-3:]] == [5, 5, 1]
    assert o["weakest"][0]["deck_id"] == outs
    assert {d["deck_id"] for d in o["decks"]} == {combos, outs}

    clock.advance(days=2)  # a missed day breaks the streak
    assert (await client.get(f"{API}/stats/overview")).json()["streak_days"] == 0


@pytest.mark.usefixtures("static_only")
async def test_deck_stats_per_card(client: httpx.AsyncClient) -> None:
    combos = await _deck_id(client, "combinatorics")
    await _review(client, combos, ["again", "easy"])
    d = (await client.get(f"{API}/stats/decks/{combos}")).json()
    reviewed = [c for c in d["cards"] if c["reviews"]]
    assert len(reviewed) == 2
    assert {c["state"] for c in reviewed} <= {"learning", "review"}
    assert all(c["state"] == "new" for c in d["cards"] if not c["reviews"])
    assert "**" not in "".join(c["label"] for c in d["cards"])
