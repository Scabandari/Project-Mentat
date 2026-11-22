import httpx

from app.content.loader import load_packs


def test_packs_validate() -> None:
    packs = load_packs()
    assert [p.slug for p in packs] == ["poker-math"]
    sections = [d.section for d in packs[0].decks]
    assert sections == sorted(sections)


async def test_only_static_cards_active_without_generators(client: httpx.AsyncClient) -> None:
    pack = (await client.get("/api/v1/packs/poker-math")).json()
    static_count = sum(1 for d in load_packs()[0].decks for c in d.cards if c.kind == "static")
    assert sum(d["card_count"] for d in pack["decks"]) == static_count
    assert pack["new_count"] == static_count
    assert pack["new_today"] == 10  # default daily limit
    assert pack["due_count"] == 0
