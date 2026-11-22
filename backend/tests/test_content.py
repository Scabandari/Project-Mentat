import httpx

from app.content.loader import load_packs
from app.generators.registry import REGISTRY


def test_packs_validate() -> None:
    packs = load_packs()
    assert [p.slug for p in packs] == ["poker-math"]
    sections = [d.section for d in packs[0].decks]
    assert sections == sorted(sections)


def test_every_registered_generator_is_used_by_a_card() -> None:
    keys = {c.generator_key for d in load_packs()[0].decks for c in d.cards if c.generator_key}
    assert set(REGISTRY) <= keys


async def test_cards_active_iff_static_or_generator_registered(client: httpx.AsyncClient) -> None:
    pack = (await client.get("/api/v1/packs/poker-math")).json()
    active = sum(
        1
        for d in load_packs()[0].decks
        for c in d.cards
        if c.kind == "static" or c.generator_key in REGISTRY
    )
    assert sum(d["card_count"] for d in pack["decks"]) == active
    assert pack["new_count"] == active
    assert pack["new_today"] == 10  # default daily limit
    assert pack["due_count"] == 0
